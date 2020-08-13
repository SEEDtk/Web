#!/usr/bin/env perl

=head1 Subsystem Health Report CGI Script

This script takes as input a subsystem ID and identifies invalid features in the subsystem.  It requires that the feature exist, and that
its assigned function contain all the roles in the subsystem column definition.  The features will be color coded as follows:

=over 4

=item Yellow

Feature exists, but does not have the correct roles.

=item Red

Feature does not exist.

=item Green

Feature has the correct role, but is not connected.

=back

Hovering over a feature in the main spreadsheet table will display the role.  There will also be a table displaying how
many times each role occurs.

The parameters are:

=over 4

=item subsystem

ID of the subsystem of interest.

=back

=cut

use strict;
use lib 'lib';
use CGI;
use TestUtils;
use WebUtils;
use XML::Simple;
use Web_Config;
use SeedUtils;		# This must go after "Web_Config" or it won't be found!
use IPC::Run3;

use constant CORE_PREFIX_URL => "https://core.theseed.org/FIG/seedviewer.cgi?page=Annotation&feature=";
use constant CORE_SUBSYSTEM_URL => "https://core.theseed.org/FIG/seedviewer.cgi?page=Subsystems;subsystem=";
use constant CORE_GENOME_URL => "https://core.theseed.org/FIG/seedviewer.cgi?page=Organism;organism=";
use constant SECTION_MARKER => "//\n";

my $start = time;
my $cgi = CGI->new();
my $ssID = $cgi->param('subsystem');
print CGI::header();
print CGI::start_html(-title => "Subsystem Health Report", -style =>  { src => "css/Basic.css" });
# Get the file directory names.
my $ssDir = "$FIG_Config::data/CoreSEED/FIG/Data/Subsystems";
my $orgDir = "$FIG_Config::data/CoreSEED/FIG/Data/Organisms";
eval {
    if (! $ssID) {
        write_index();
    } else {
        write_report();
    }
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();

## Write the master index.
sub write_index {
    print CGI::h1("Subsystem Index");
    opendir(my $dh, $ssDir) || die "Could not open subsystem directory: $!";
    my @subs = sort { ssName($a) cmp ssName($b) } grep { -s "$ssDir/$_/spreadsheet" } readdir $dh;
    closedir $dh;
    print CGI::start_div({ id => 'Pod' });
    print CGI::start_ol();
    for my $sub (@subs) {
        if (substr($sub, 0, 1) ne '.') {
            print CGI::li(CGI::a({ href => "subsystem.cgi?subsystem=$sub"}, ssName($sub)));
        }
    }
    print CGI::end_ol();
    print CGI::end_div();
}


## Write the health report.
sub write_report {
    my $debug = $cgi->param('debug');
    eval {
        my @cmd = split /\s/, "java -Dlogback.configurationFile=$FIG_Config::mod_base/kernel/jars/weblogback.xml -jar $FIG_Config::mod_base/kernel/jars/web.utils.jar";
        push @cmd, $ssID, "$FIG_Config::data/CoreSEED/FIG/Data";
        my (@err, @out);
        my $rc = IPC::Run3::run3(\@cmd, \undef, undef, \@err);
        if ($debug) {
            print CGI::h2("Log Messages");
            print CGI::p("Return code is $rc.");
            print CGI::ul(CGI::li(\@err));
        }
    };
    if ($@) {
        print CGI::blockquote($@);
    }
    print CGI::end_html();
}

sub read_functions {
    my ($genome) = @_;
    my $retVal;
    # Process the deleted features.
    my %deleted;
    for my $type (qw(peg rna)) {
        if (open(my $ih, '<', "$orgDir/$genome/Features/$type/deleted.features")) {
            while (! eof $ih) {
                my $line = <$ih>;
                chomp $line;
                $deleted{$line} = 1;
            }
        }
    }
    my $funFile = "$orgDir/$genome/assigned_functions";
    if (-s $funFile) {
        open(my $ih, '<', $funFile) || die "Could not open assigned functions for $genome: $!";
        $retVal = {};
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            my ($id, $function) = split /\t/, $line;
            if (! $deleted{$id}) {
                $retVal->{$id} = $function;
            }
        }
    }
    return $retVal;
}

## Write the role table.  This tells us how many times each role is found and what other roles are found.
sub write_role_table {
    my ($roles, $abbrs, $countHashes, $correctRole, $disPegs) = @_;
    print CGI::h2(CGI::a({ name => 'roles'},"Role Summary"));
    print CGI::start_table();
    print CGI::Tr(CGI::th("Abbr"), CGI::th("Functional Role"), CGI::th("Correct"), CGI::th("Disconnected"),
            CGI::th("Bad Roles"));
    for (my $i = 0; $i < @$roles; $i++) {
        # Build the incorrect versions string.
        my $countHash = $countHashes->[$i];
        my @versions;
        for my $badRole (sort { scalar(@{$countHash->{$b}}) <=> scalar(@{$countHash->{$a}}) } keys %$countHash) {
            my $badH = $countHash->{$badRole};
            push @versions, CGI::li(scalar(@$badH) . ": " . $badRole . " [" .
                join(", ", map { display_peg($_) } @$badH) . "]");
        }
        my $versionString = (scalar @versions ? CGI::ul(@versions) : "&nbsp;");
        # Print the information for this row.
        print CGI::Tr(CGI::td($abbrs->[$i]), CGI::td($roles->[$i]), alert_num($correctRole->[$i]),
            fancy_num($disPegs->[$i]), CGI::td($versionString));
    }
    print CGI::end_table();
}

## Display a number in a cell, and highlight it if it is non-zero.
sub fancy_num {
    my ($num) = @_;
    my $retVal;
    if ($num > 0) {
        $retVal = CGI::td({ class => 'num highlight' }, $num);
    } else {
        $retVal = CGI::td("&nbsp;");
    }
    return $retVal;
}

## Display a number in a cell, and highlight it if it is zero.
sub alert_num {
    my ($num) = @_;
    my $retVal;
    if ($num > 0) {
        $retVal = CGI::td({ class => 'num' }, $num);
    } else {
        $retVal = CGI::td({ class => 'highlight num'}, '0');
    }
    return $retVal;

}

## Convert a subsystem ID to a name.
sub ssName {
    my ($retVal) = @_;
    $retVal =~ tr/_/ /;
    return $retVal;
}

## Return the display string for a peg.
sub display_peg {
    my ($peg, $mode) = @_;
    my $retVal;
    if ($mode eq 'missing') {
        $retVal = CGI::span({ class => 'missing' }, $peg);
    } else {
        $retVal = CGI::a({ href => (CORE_PREFIX_URL . $peg), target => "_blank", class => $mode }, $peg);
    }
}
1;
