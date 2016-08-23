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
use URI::Escape;  # uri_escape
use CGI;

=head1 New Alexa Script for PATRIC Access

This is the new script for accessing PATRIC from Alexa.

=head2 Parameters

=over 4

=item account

The account parameter for this session. This is used to compute the subdirectory for the data storage. Multiple directory
levels are separated by an exclamation point (C<!>).

=item save

The name of the output. A file will be created with this name and the suffix C<.set> or C<.tbl>. Output can be in 
the form of sets or tables: a set has a single column; a table has multiple named columns, tab-delimited.

=item request

The type of request. The following requests are supported.

=over 8

=item get_genomes

Create an output set of genome IDs.

=item set_ops

Create an output set by merging input sets (optionally excluding records from other sets). Here the C<from> and C<not>
parameters are supported, but not the C<constraint>.

=item amr_genomes

Filter a set of genomes by anti-microbial resistance data.

=back

=item 

=item from

Specifies a set from which IDs are to be taken.

=item not

Specifies a set whoses IDs are to be excluded.

=item pick

Reduce the input set to a random selection of no more than N elements.

=item constraint

A list of rules applied to a query. There may be multiple of these constraints. The individual components of each constraint are
separated by commas.

=over 8

=item match

Specifies a match constraint. This constraint is specified as part of the PATRIC query, and it performs a substring match for
string fields and an exact match for numeric fields. The subparameters are (1) the field to match and (2) the value to match
against it. An asterisk (C<*>) serves as a wild card.

=back

=item label

Specifies a string that should be used to label the set or table. It will be put into a file with the same name as the
set or table and a suffix of C<.lbl>.

=back

=cut

my $cgi = new CGI;
# We will put the output in here. 
my $result = [];
# Get a header.
print CGI::header('text/plain');
eval {
    my $p3 = P3DataAPI->new();
    # Compute the working directory.
    my $acct = $cgi->param('account');
    die "No account specified." if ! $acct;
    $acct =~ s/!/\//g;
    my $sessionDir = "$FIG_Config::temp/$acct";
    # This will be our output file handle and label (if any).
    my ($oh, $label);
    # Insure our directory exists.
    if (! -d $sessionDir) {
        File::Copy::Recursive::pathmk($sessionDir) or die "Could not create session directory: $!";
    }
    # Determine the request.
    my $request = $cgi->param('request');
    if (! $request) {
        die "No request specified.";
    } elsif ($request eq 'get_genomes') {
        ($oh, $label) = ComputeOutputFile(set => $cgi, $sessionDir);
        my $constraintList = ComputeConstraints($cgi);
        # Determine whether this is an ID-based request or not.
        if (scalar $cgi->param('from')) {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir);
            # Ask PATRIC for results.
            $result = P3Utils::get_data_keyed($p3, genome => $constraintList, ['genome_id'], $idList, 'genome_id');
        } else {
            # Ask PATRIC for all qualifying genomes.
            $result = P3Utils::get_data($p3, genome => $constraintList, ['genome_id']);
        }
    } elsif ($request eq 'set_ops') {
        ($oh, $label) = ComputeOutputFile(set => $cgi, $sessionDir);
        # Insure we have a from set.
        if (! scalar $cgi->param('from')) {
            die "set_ops requires a \"from\" parameter.";
        } else {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir);
            # Convert the IDs to results.
            $result = [map { [$_] } @$idList];
        }
    } elsif ($request eq 'amr_genomes') {
        ($oh, $label) = ComputeOutputFile(set => $cgi, $sessionDir);
        my $constraintList = ComputeConstraints($cgi);
        # Insure we have a from set.
        if (! scalar $cgi->param('from')) {
            die "amr_genomes requires a \"from\" parameter.";
        } else {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir);
            # Ask PATRIC for results.
            $result = P3Utils::get_data_keyed($p3, genome_drug => $constraintList, ['genome_id'], $idList, 'genome_id');
            # $result = P3Utils::get_data_keyed($p3, genome_drug => [], ['genome_id', 'antibiotic', 'resistant_phenotype'], $idList, 'genome_id');
        }
    } else {
        die "Invalid request $request.\n";
    }
    PrintResult($oh, $result);
    # Insure there is some output if we spooled the results to a file.
    if ($oh) {
        $label ||= "result set";
        print "$label\n";
    }
};
if ($@) {
    print "ERROR: $@\n";
}

# Return the output file handle, or undef if there is no output to a file.
sub ComputeOutputFile {
    my ($type, $cgi, $sessionDir) = @_;
    # This will be the return outut handle.
    my $retVal;
    # Get the set/table name.
    my $name = $cgi->param('save');
    # Get the set/table label.
    my $label = $cgi->param('label');
    # Only proceed if we have one.
    if ($name) {
        # Suffix the type.
        $name .= ".$type";
        # Open the file for output.
        open($retVal, ">$sessionDir/$name") || die "Could not open output $type: $!";
        # Create the label.
        if ($label) {
            open(my $oh, ">$sessionDir/$name.lbl") || die "Could not open label file for $name: $!";
            print $oh "$label\n";
        }
    }
    return ($retVal, $label);
}


# Return a list of PATRIC-style constraints from the CGI-specified constraints.
sub ComputeConstraints {
    my ($cgi) = @_;
    # This will contain the output constraint clauses.
    my @retVal;
    # Get the list of constraints.
    my @constraints = $cgi->param('constraint');
    # Loop through them, adding them to the output list.
    for my $constraint (@constraints) {
        my ($type, $field, @values) = split /,/, $constraint;
        # Process according to the type.
        if ($type eq 'match') {
            push @retVal, ['eq', $field, $values[0]];
        }
    }
    # Return the constraint list.
    return \@retVal;
}

# Return a list of the IDs to use in selecting objects. This involves parsing the FROM and NOT
# parameters.
sub ComputeInputIds {
    my ($cgi, $sessionDir) = @_;
    # This will be the output ID list.
    my @retVal;
    # Create a hash of the NOT values.
    my %notIDs;
    # Get the list of NOT sets.
    my @notSets = $cgi->param('not');
    # Loop through them, filling the hash.
    for my $notSet (@notSets) {
        my $notFile = "$sessionDir/$notSet.set";
        open(my $ih, "<$notFile") || die "Could not open ID exclusion set $notSet: $!";
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            $notIDs{$line} = 1;
        }
    }
    # Now loop through the FROM sets, filling the output.
    my @fromSets = $cgi->param('from');
    for my $fromSet (@fromSets) {
        my $fromFile = "$sessionDir/$fromSet.set";
        open (my $ih, "<$fromFile") || die "Could not open ID inclusion set $fromSet: $!";
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            if (! $notIDs{$line}) {
                push @retVal, $line;
            }
        }
    }
    # Is there a pick specified?
    my $pick = $cgi->param('pick');
    if ($pick) {
        # Validate the pick number.
        if ($pick =~ /\D/) {
            die "Invalid pick amount specification $pick.";
        } elsif ($pick < scalar @retVal) {
            # Here we need to reduce the ID list. Shuffle random
            # elements to the top.
            for (my $i = 0; $i < $pick; $i++) {
                my $j = int(rand $pick);
                ($retVal[$i], $retVal[$j]) = ($retVal[$j], $retVal[$i]);
            }
            # Slice off the end of the list.
            splice @retVal, $pick;
        }
    }
    # Return the result list.
    return \@retVal;
}

# Output the result as a tab-delimited file.
sub PrintResult {
    my ($oh, $result) = @_;
    $oh //= \*STDOUT; # Default to the standard output
    for my $item (@$result) {
        print $oh join("\t", @$item) . "\n";
    }
}
