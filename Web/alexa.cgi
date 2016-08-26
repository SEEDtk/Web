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

The name of the output. A file will be created with this name and the suffix C<.set> or C<.table>. Output can be in 
the form of sets or tables: a set has a single column; a table has multiple named columns, tab-delimited.

=item request

The type of request. The following requests are supported.

=over 8

=item get_genomes

Create an output set of genome IDs. The constraints should be on fields in the L</genome> table.

=item set_ops

Create an output set by merging input sets (optionally excluding records from other sets). Here the C<from> and C<not>
parameters are supported, but not the C<constraint>.

=item amr_genomes

Filter a set of genomes by anti-microbial resistance data. The constraints should be on fields in the L</genome_drug>
table.

=item get_genome_table

Create an output table of genome data. The constraints and display fields should be based in the L</genome> table.

=item get_drug_table

Create an output table of genome AMR data. The constraints and display fields should be based in the L<genome_drug> table.
If C<from> and C<not> parameters are specified, they will be presumed to refer to genome IDs.

=item list_sets

List all of the sets currently in the workspace.

=item list_tables

List all of the tables currently in the workspace.

=item show_table

Display the contents of the specified table. The table should be specified in the C<from> parameter. (To show a set, use
B<set_ops> with only a C<from> parameter.)

=back

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

=item susceptible

Specifies that a genome is susceptible to a drug. The subparameter is the drug name. This constraint is only allowed on
requests against the genome_drug table.

=item resistant

Specifies that a genome is resistant to a drug. The subparameter is the drug name. This constraint is only allowed on
requests against the genome_drug table.

=item exclude

Specifies a don't-match constraint. This constraint is specified as part of the PATRIC query, and it performs a substring match
for string fields and an exact match for numeric fields. Records are only accepted if they do not match. The subparameters are (1)
the field to match and (2) the value to match against it. An asterisk (C<*>) serves as a wild card.

=back

=item display

The names of the fields to include in the output, specified as a comma-delimited list. This is only 
used for table-producing commands. Note that you must specify the ID if you want the ID included.

=item label

Specifies a string that should be used to label the set or table. It will be put into a file with the same name as the
set or table and a suffix of C<.lbl>.

=back

=head2 Notes on Fields

When forming C<match> constraints, it is useful to know the names of some of the common fields in the PATRIC database.
The complete schema can be found at L<https://github.com/PATRIC3/patric_solr>.  To look at the inndividual schema for 
an object, go into the B<schema.xml> file of the C<conf> subdirectory.

=head3 genome

This corresponds to the PATRIC B<genome> object.

=over 4

=item genome_id

the unique genome ID

=item genome_name

the scientific name

=item taxon_id

the NCBI taxonomic ID

=item genome_length

number of base pairs

=item gc_content

percentage GC content

=back

=head3 genome_drug

This corresponds to the PATRIC B<genome_amr> object.

=over 4

=item genome_id

The ID of the relevant genome.

=item genome_name

The name of the relevant genome.

=item antibiotic

The name of the relevant drug.

=item resistant_phenotype

Either C<Resistant>, C<Susceptible>, or an empty string (unknown), indicating the genome's relationship to the drug.

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
    # This will be set to 1 if we have headers.
    my $headers = 0;
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
    } elsif ($request eq 'get_genome_table') {
        ($oh, $label) = ComputeOutputFile(table => $cgi, $sessionDir);
        $headers = 1;
        my $constraintList = ComputeConstraints($cgi);
        # Get the display fields. Default to ID and name.
        my $displayList = ComputeFields($cgi);
        if (! scalar @$displayList) {
            $displayList = ['genome_id', 'genome_name'];
        }
        # Determine whether this is an ID-based request or not.
        if (scalar $cgi->param('from')) {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir);
            # Ask PATRIC for results.
            $result = P3Utils::get_data_keyed($p3, genome => $constraintList, $displayList, $idList, 'genome_id');
        } else {
            # Ask PATRIC for all qualifying genomes.
            $result = P3Utils::get_data($p3, genome => $constraintList, $displayList);
        }
        # Add the headers.
        unshift @$result, $displayList;
    } elsif ($request eq 'get_drug_table') {
        ($oh, $label) = ComputeOutputFile(table => $cgi, $sessionDir);
        $headers = 1;
        my $constraintList = ComputeConstraints($cgi);
        # Get the display fields. Default to ID and resistance info.
        my $displayList = ComputeFields($cgi);
        if (! scalar @$displayList) {
            $displayList = ['genome_id', 'antibiotic', 'resistant_phenotype'];
        }
        # Determine whether this is an ID-based request or not.
        if (scalar $cgi->param('from')) {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir);
            # Ask PATRIC for results.
            $result = P3Utils::get_data_keyed($p3, genome_drug => $constraintList, $displayList, $idList, 'genome_id');
        } else {
            # Ask PATRIC for all qualifying genomes.
            $result = P3Utils::get_data($p3, genome_drug => $constraintList, $displayList);
        }
        # Add the headers.
        unshift @$result, $displayList;
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
            my $idResult = P3Utils::get_data_keyed($p3, genome_drug => $constraintList, ['genome_id'], $idList, 'genome_id');
            # Merge duplicates.
            my %found = map { $_->[0] => 1 } @$idResult;
            $result = [map { [$_] } sort keys %found];
        }
    } elsif ($request eq 'list_sets') {
        # Display information about all the sets.
        $result = ListItems('set', $sessionDir);
    } elsif ($request eq 'list_tables') {
        # Display information about all the tables.
        $result = ListItems('table', $sessionDir);
    } elsif ($request eq 'show_table') {
        my $name = $cgi->param('from');
        die "No table name specified." if ! $name;
        open(my $ih, "<$sessionDir/$name.table") || die "Could not access table $name: $!";
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            my @fields = split /\t/, $line;
            push @$result, \@fields;
        }
    } elsif ($request eq 'describe_set') {
        my $name = $cgi->param('from');
        die "No set name specified." if ! $name;
        $result = [[ DescribeItem(set => $name, $sessionDir) ]];
    } elsif ($request eq 'describe_table') {
        my $name = $cgi->param('from');
        die "No table name specified." if ! $name;
        $result = [[ DescribeItem(table => $name, $sessionDir) ]];
    } else {
        die "Invalid request $request.\n";
    }
    PrintResult($oh, $result);
    # Insure there is some output if we spooled the results to a file.
    if ($oh) {
        $label ||= "result set produced with no label";
        print "$label\n";
        my $lines = scalar(@$result) - $headers;
        print "$lines lines output.\n";
    }
};
if ($@) {
    print "ERROR: $@\n";
}

# List all the items of the specified type in the workspace.
sub ListItems {
    my ($type, $sessionDir) = @_;
    # Get all the files of the specified type in the workspace.
    my $suffix = ".$type";
    my $suffixLen = length $suffix;
    opendir(my $dh, $sessionDir) || die "Could not open session directory: $!";
    my @files = sort grep { substr($_,-$suffixLen) eq $suffix } readdir $dh;
    # The descriptions will be put in here.
    my @retVal;
    # Loop through the files.
    for my $file (@files) {
        # Get the real name of the file.
        my ($name) = split /\./, $file;
        my $response = DescribeItem($type, $name, $sessionDir);
        # Push the description.
        push @retVal, $response;
    }
    # Return the result as a result set.
    if (! @retVal) {
        die "No $type items found in workspace.";
    }
    return [map { [$_] } @retVal];
}

# Describe a set or table.
sub DescribeItem {
    my ($type, $name, $sessionDir) = @_;
    my $retVal;
    # Get the file name.
    my $fileName = "$sessionDir/$name.$type";
    if (! -f $fileName) {
        $retVal = ucfirst "$type $name does not exist.";
    } else {
        # Read the label (if any).
        my $label;
        my $labelFile = "$fileName.lbl";
        if (open(my $lh, "<$labelFile")) {
            $label = <$lh>;
            chomp $label;
        } else {
            $label = "unlabeled";
        }
        # Count the lines.
        open(my $ih, "<$fileName") || die "Could not open $type $name: $!";
        my $lineCount = 0;
        $lineCount++ while (<$ih>);
        $lineCount-- if ($type eq 'table');
        # Format the description.
        $retVal = ucfirst "$type $name is $label and contains $lineCount records.";
    }
    return $retVal;
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
        # Compute the display name.
        my $display = ucfirst $type . ' ' . $name;
        # Suffix the type to the file name.
        $name .= ".$type";
        # Open the file for output.
        open($retVal, ">$sessionDir/$name") || die "Could not open output $type: $!";
        # Create the label.
        if ($label) {
            open(my $oh, ">$sessionDir/$name.lbl") || die "Could not open label file for $name: $!";
            print $oh "$label\n";
            $label = "$display now contains $label.";
        } else {
            $label = "$display now contains the result.";
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
        } elsif ($type eq 'exclude') {
            push @retVal, ['ne', $field, $values[0]];
        } elsif ($type eq 'susceptible' || $type eq 'resistant') {
            push @retVal, ['eq', 'resistant_phenotype', ucfirst $type], ['eq', 'antibiotic', $field];
        } else {
            die "Invalid constraint category $type.";
        }
    }
    # Return the constraint list.
    return \@retVal;
}

# Return the list of fields to display.
sub ComputeFields {
    my ($cgi) = @_;
    my $line = $cgi->param('display');
    my @retVal = split /,/, $line;
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
