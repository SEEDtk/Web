#!/usr/bin/env perl

#
# Copyright (c) 2003-2006 University of Chicago and Fellowship
# for Interpretations of Genomes. All Rights Reserved.
#
# This file is part of the SEED Toolkit.
#
# The SEED Toolkit is free software. You can redistribute
# it and/or modify it under the terms of the SEED Toolkit
# Public License.
#
# You should have received a copy of the SEED Toolkit Public License
# along with this program; if not write to the University of Chicago
# at info@ci.uchicago.edu or the Fellowship for Interpretation of
# Genomes at veronika@thefig.info or download a copy from
# http://www.theseed.org/LICENSE.TXT.
#


use strict;
use lib::Web_Config;
use P3DataAPI;
use P3Utils;
use Data::Dumper;
use File::Copy::Recursive;
use CGI;
use Job;
use LWP::UserAgent;
use URI::Escape;
use Shrub;
use SeedUtils;
use GenomeTypeObject;

=head1 Utility Script for SEEDtk Web Interface

This CGI script executes simply SEEDtk commands. The output is put in a subdirectory of C<WebSpaces> underneath the
SEEDtk data directory. The user specifies an I<account> in each invocation that contains the subdirectory path.

=head2 Parameters

=over 4

=item account

The account parameter for this session. This is used to compute the subdirectory for the data storage. Multiple directory
levels are separated by an exclamation point (C<!>).

=item request

The type of request. The following requests are supported.

=over 8

=item get_gto

Create a L<GenomeTypeObject> for the specified genome. The genome ID is specified in the C<genome_id> parameter.

=item gto_quality

Run a quality check on a GTO in the workspace and produce a quality report page.

=back

=item genome_id

The ID of a genome to operate on.

=back

=cut

# Create the CGI object.
my $cgi = new CGI;
# Start the web page.
print CGI::header(-type => 'text/html');
eval {
    my $p3 = P3DataAPI->new();
    # Insure the default umask doesn't screw us up.
    if (! $FIG_Config::win_mode) {
        umask 0;
    }
    # Compute the working directory.
    my $acct = $cgi->param('account');
    die "No account specified." if ! $acct;
    $acct =~ s/!/\//g;
    my $sessionDir = "$FIG_Config::data/WebSpaces/$acct";
    # Insure our directory exists.
    if (! -d $sessionDir) {
        File::Copy::Recursive::pathmk($sessionDir) or die "Could not create session directory: $!";
    }
    # Determine the request.
    my $request = $cgi->param('request');
    if (! $request) {
        die "No request specified.";
    } elsif ($request eq 'get_gto') {
        my $genomeID = $cgi->param('genome_id');
        if (! $genomeID) {
            die "No genome ID specified.";
        } elsif (! ($genomeID =~ /^(\d+\.\d+)/)) {
            die "Invalid genome ID specified.";
        } else {
            # The GTO will be put in here.
            my $gto = get_gto($genomeID);
            if ($gto) {
                $gto->destroy_to_file("$sessionDir/$genomeID.gto");
                print CGI::p("Genome written to $sessionDir/$genomeID.gto.\n");
            }
        }
    } elsif ($request eq 'qual_gto') {
        my $genomeID = $cgi->param('genome_id');
        if (! $genomeID) {
            die "No genome ID specified.";
        } elsif (! ($genomeID =~ /^(\d+\.\d+)/)) {
            die "Invalid genome ID specified.";
        } else {
            my $gtoFile = "$sessionDir/$genomeID.gto";
            if (! -s $gtoFile) {
                die "No GTO file founr for $genomeID.\n";
            } else {
                qual_gto($gtoFile, $sessionDir);
            }
        }
    } else {
        die "Invalid request specified.";
    }
};
if ($@) {
    print CGI::blockquote("ERROR: $@\n");
}

sub get_gto {
    my ($genomeID) = @_;
    # This will be the return value.
    my $retVal;
    # Check the Shrub.
    my $shrub = Shrub->new();
    my ($genomeName) = $shrub->GetFlat('Genome', 'Genome(id) = ?', [$genomeID], 'name');
    if ($genomeName) {
        require Shrub::GTO;
        $retVal = Shrub::GTO->new($shrub, $genomeID);
        print CGI::p("$genomeID: $genomeName found in Shrub.");
    } else {
        # Check PATRIC.
        my $p3 = P3DataAPI->new();
        $retVal = $p3->gto_of($genomeID);
        if (! $retVal) {
            die "$genomeID not found.";
        } else {
            my $name = $retVal->{scientific_name};
            print CGI::p("$genomeID: $name found in PATRIC.");
        }
    }
    return $retVal;
}

sub qual_gto {
    my ($gtoFile, $sessionDir) = @_;
    if (-d "$sessionDir/EvalCon") {
        File::Copy::Recursive::pathrmdir("$sessionDir/EvalCon") || die "Could not erase EvalCon output directory: $!";
    }
    # Select the EvalCon files.
    my $predictors = "$FIG_Config::global/FunctionPredictors";
    my $rolesToUse = "$FIG_Config::global/roles.to.use";
    my $roleFile = "$FIG_Config::global/roles.in.subsystems";
    # Read the detail template.
    my $tDir = "$FIG_Config::mod_base/kernel/lib/BinningReports";
    open(my $th, "<$tDir/details.tt") || die "Could not open detail template file: $!";
    my $detailsT = join("", <$th>);
    close $th; undef $th;
    # Build the HTML prefix and suffix.
    my $prefix = "<html><head>\n<style type=\"text/css\">\n";
    open($th, "<$tDir/packages.css") || die "Could not open style file: $!";
    while (! eof $th) {
        $prefix .= <$th>;
    }
    close $th; undef $th;
    $prefix .= "</style></head><body>\n";
    my $suffix = "\n</body></html>\n";
    # Run the quality checks.
    my $cmd = "check_gto --eval --quiet $sessionDir/EvalG $gtoFile";
    warn "Running $cmd.\n";
    SeedUtils::run($cmd);
    $cmd = "gto_consistency $gtoFile $sessionDir/EvalCon $predictors $roleFile $rolesToUse";
    warn "Running $cmd.\n";
    SeedUtils::run($cmd);
    # Create the role maps.
    my (%cMap, %nameMap);
    open(my $rh, '<', $roleFile) || die "Could not open role file: $!";
    while (! eof $rh) {
        my $line = <$rh>;
        my ($id, $cksum, $name) = P3Utils::get_fields($line);
        $cMap{$cksum} = $id;
        $nameMap{$id} = $name;
    }
    # Prepare for the quality report.
    my $gto = GenomeTypeObject->create_from_file($gtoFile);
    require BinningReports;
    BinningReports::UpdateGTO($gto, "$sessionDir/EvalCon", "$sessionDir/EvalG", \%cMap);
    # Load the detail template.
    my $html = BinningReports::Detail({}, undef, \$detailsT, $gto, \%nameMap);
    print "$prefix\n$html\n$suffix\n";
}