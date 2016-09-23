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

The type of request. The following query-related requests are supported.

=over 8

=item amr_genomes

Filter a set of genomes by anti-microbial resistance data. The constraints should be on fields in the L</genome_drug>
table. The C<from> parameter is required.

=item get_drug_table

Create an output table of genome AMR data. The constraints and display fields should be based in the L</genome_drug> table.
If C<from> and C<not> parameters are specified, they will be presumed to refer to genome IDs.

=item get_genome_table

Create an output table of genome data. The constraints and display fields should be based in the L</genome> table.

=item get_genomes

Create an output set of genome IDs. The constraints should be on fields in the L</genome> table.

=back

The following data management requests are supported.

=over 4

=item clear

Clear all items from the workspace.

=item clear_sets

Delete all the sets from the workspace.

=item clear_tables

Delete all the tables from the workspace.

=item delete_sets

Delete the sets listed in the C<from> parameter.

=item delete_tables

Delete the tables listed in the C<from> parameter.

=item describe_set

Display information about the specified set in the workspace.

=item describe_table

Display information about the specified table in the workspace.

=item list_sets

List all of the sets currently in the workspace.

=item list_tables

List all of the tables currently in the workspace.

=item set_ops

Create an output set by merging input sets (optionally excluding records from other sets). Here the C<from> and C<not>
parameters are supported, but not the C<constraint>.

=item show_table

Display the contents of the specified table. The table should be specified in the C<from> parameter. (To show a set, use
B<set_ops> with only a C<from> parameter.)

=back

The following background task (job) management requests are supported.

=over 4

=item task

Run background task. The C<task>, C<taskname>, and C<taskparms> parameters are used for this.

=item job_check

Do a complete check of the job status. This overrides C<checkjobs>, which checks only for completed jobs.

=item job_purge

Removes all data relating to jobs with an C<informed> status.

=back

Finally, there are the following miscellaneous requests.

=over 4

=item define

Return the definition string for an intent. Uses the C<intent> parameter. The definitions are read from the C<intents.json>
file in the C<lib> subdirectory.

=item show_peg

Display the specified feature on the user's compare regions web page (currently
L<http://p3.theseed.org/qa/compare_regions/fig%7C83332.12.peg.1?channel=alexa>). The feature will be from the set
indicated by the C<from> parameter at the position indicated by the C<position> parameter. A position of C<1> will
display the first feature, C<2> the second feature, and so forth.

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

=item task

The type of task to run in the background.

=over 8

=item test

The test application L<AlexaTest.pl>. For the application, you can specify the following command-line parms.

=over 12

=item time

The number of 2-second intervals to wait.

=back

=item families

The signature families application L<AlexaSignatureFamilies.pl>. For this application, you must specify two genome sets--
C<from> and C<not>-- and a result table (C<save>). In addition, you can specify the following command-line parms.

=over 12

=item minIn

Minimum fraction of from-genomes that must contain a family for it to be a signature.

=item maxOut

Maximum fraction of the not-genomes that can contain a family for it to be a signature.

=back

=item cluster_pegs

The cluster peg search application L<AlexaDistinguishingClusterPegs.pl>. For this application, you must specify two genome sets--
C<from> and C<not>-- and a result table (C<save>). This application produces both a result table and a result set, but they will
have the same name. Rather than a single comparison between sets, the cluster peg application runs multiple iterations using
subsets randomly selected from each input set. You can specify the following command-line parms.

=over 12

=item minIn

Minimum fraction of from-genomes that must contain a family for it to be a signature.

=item maxOut

Maximum fraction of the not-genomes that can contain a family for it to be a signature.

=item size

Number of genomes to pick into each subset.

=item iterations

Number iterations to run.

=item pegs

Number of pegs to return in the output set.

=item distance

Maximum base-pair distance between the midpoints of two features in order for them to be
considered close. The default is 2000.

=back

=back

=item taskname

The name to give to the task.

=item taskparm

A parameter string to pass to the application. This option is multi-valued. Multiple parameters should be passed as
multiple values. Command-line options should use the equals form (e.g. C<--min=10>).

=item checkjobs

If TRUE, then the output will be suffixed by a summary of recently-completed background jobs.

=item intent

The name of an intent for the C<define> request.

=back

=head2 Notes on Fields

When forming constraints, it is necessary to know how to name the fields in the PATRIC database.
The complete schema can be found at L<https://github.com/PATRIC3/patric_solr>.  To look at the inndividual schema for
an object, go into the B<schema.xml> file of the C<conf> subdirectory. For the Alexa interface, we have readable
names for each supported field. These readable names are the ones that must be suppled in the C<display> parameter.

=head3 genome

This corresponds to the PATRIC B<genome> object.

=over 4

=item genome_id

the unique genome ID. Must be specified as C<id>.

=item genome_name

the scientific name. Must be specified as C<name>.

=item taxon_id

the NCBI taxonomic ID. May be specified as C<taxon ID>, C<taxonomic number>,

=item genome_length

number of base pairs. Must be specified as C<size>.

=item gc_content

percentage GC content. May be specified as C<gc content>, C<guanine cytosine content>, or C<G C content>.

=back

=head3 genome_drug

This corresponds to the PATRIC B<genome_amr> object.

=over 4

=item genome_id

The ID of the relevant genome. Must be specified as C<id>.

=item genome_name

The name of the relevant genome. Must be specified as C<name>.

=item antibiotic

The name of the relevant drug. Must be specified as C<antibiotic> or C<drug>.

=item resistant_phenotype

Either C<Resistant>, C<Susceptible>, or an empty string (unknown), indicating the genome's relationship to the drug.
Must be specified as C<resistance type> or C<resistance phenotype>.

=back

=cut

## These constants define the data model.
use constant OBJECT_TYPE =>
        { amr_genomes => 'genomes', get_drug_table => 'genomes', get_genome_table => 'genomes',
          get_genomes => 'genomes', set_ops => 'items' };
use constant RETURNS_TABLE =>
        { get_drug_table => 1, get_genome_table => 1 };
use constant FIELD_NAME_TO_PATRIC =>
        { genomes => { 'id' => 'genome_id', 'name' => 'genome_name', 'taxonomic number' => 'taxon_id', 'taxon id' => 'taxon_id',
                       'taxon i d' => 'taxon_id', 'taxonomic id' => 'taxon_id', 'taxonomic i d' => 'taxon_id',
                       'size' => 'genome_length', 'gc content' => 'gc_content', 'guanine cytosine content' => 'gc_content',
                       'g c content' => 'gc_content', 'drug' => 'antibiotic', 'antibiotic' => 'antibiotic',
                       'resistance type' => 'resistant_phenotype', 'resistance phenotype' => 'resistant_phenotype' },
        };
use constant FIELD_NAME =>
        { genomes => { genome_id => 'id', genome_name => 'name', taxon_id => 'taxonomic number',
                       genome_length => 'size', gc_content => 'G C content', antibiotic => 'drug',
                       resistant_phenotype => 'resistance type' }
        };

my $cgi = new CGI;
# We will put the output in here.
my $result = [];
# This will be set if we want to check jobs.
my $checkJobs = $cgi->param('checkjobs');;
# Get a header.
print CGI::header('text/plain');
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
    my $sessionDir = "$FIG_Config::alexa/$acct";
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
    } elsif ($request eq 'task') {
        my $name = $cgi->param('taskname');
        die "No task name specified." if ! $name;
        my $script = $cgi->param('task');
        # We will put parameters in here.
        my @parms;
        # This will be the command.
        my $command;
        if ($script eq 'families' || $script eq 'cluster_pegs') {
            $command = ($script eq 'families' ? 'AlexaSignatureFamilies' : 'AlexaDistinguishingClusterPeg');
            @parms = grep { $_ } $cgi->param('taskparm');
            my @from = GetNames(from => $cgi, 1);
            my @not = GetNames('not' => $cgi, 1);
            push @parms, @from, @not;
            my $save = $cgi->param('save');
            die "No result table specified." if ! $save;
            push @parms, $save;
        } elsif ($script eq 'test') {
            $command = 'AlexaTest';
            @parms = $cgi->param('taskparm');
        } else {
            die "Invalid background script $script.";
        }
        my $statusFile = Job::Create($sessionDir, $name, $command, @parms);
        sleep 1;
        if (-f $statusFile) {
            print "Job $name started.\n";
        } else {
            print "Job $name is starting.\n";
        }
    } elsif ($request eq 'job_check') {
        # Check the background job queue.
        my $jobList = Job::Check($sessionDir, 'complete');
        # Suppress any after-check.
        $checkJobs = '';
        if (scalar @$jobList) {
            print join("\n", @$jobList, "");
        } else {
            print "No active jobs.\n";
        }
    } elsif ($request eq 'job_purge') {
        my $count = Job::Purge($sessionDir);
        if ($count == 0) {
            $count = "No jobs";
        } elsif ($count == 1) {
            $count = "One job";
        } else {
            $count = "$count jobs";
        }
        print "$count purged.\n";
    } elsif ($request eq 'get_genomes') {
        ($oh, $label) = ComputeOutputFile(set => $cgi, $sessionDir);
        my $constraintList = ComputeConstraints($cgi);
        # Determine whether this is an ID-based request or not.
        my @froms = GetNames(from => $cgi);
        if (scalar @froms) {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir, \@froms);
            # Ask PATRIC for results.
            $result = P3Utils::get_data_keyed($p3, genome => $constraintList, ['genome_id'], $idList, 'genome_id');
        } else {
            # Ask PATRIC for all qualifying genomes.
            $result = P3Utils::get_data($p3, genome => $constraintList, ['genome_id']);
        }
    } elsif ($request eq 'get_genome_table') {
        # Get the display fields. Default to ID and name.
        my $displayList = ComputeFields(genomes => $cgi);
        if (! scalar @$displayList) {
            $displayList = ['genome_id', 'genome_name'];
        }
        # Compute the output file and label.
        ($oh, $label) = ComputeOutputFile(table => $cgi, $sessionDir, $displayList);
        $headers = 1;
        my $constraintList = ComputeConstraints($cgi);
        # Determine whether this is an ID-based request or not.
        my @froms = Getnames(from => $cgi);
        if (scalar @froms) {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir, \@froms);
            # Ask PATRIC for results.
            $result = P3Utils::get_data_keyed($p3, genome => $constraintList, $displayList, $idList, 'genome_id');
        } else {
            # Ask PATRIC for all qualifying genomes.
            $result = P3Utils::get_data($p3, genome => $constraintList, $displayList);
        }
        # Add the headers.
        unshift @$result, $displayList;
    } elsif ($request eq 'get_drug_table') {
        # Get the display fields. Default to ID and resistance info.
        my $displayList = ComputeFields(genomes => $cgi);
        if (! scalar @$displayList) {
            $displayList = ['genome_id', 'antibiotic', 'resistant_phenotype'];
        }
        # Compute the output file and label.
        ($oh, $label) = ComputeOutputFile(table => $cgi, $sessionDir, $displayList);
        $headers = 1;
        my $constraintList = ComputeConstraints($cgi);
        # Determine whether this is an ID-based request or not.
        my @froms = GetNames(from => $cgi);
        if (scalar @froms) {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir, \@froms);
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
        my @froms = GetNames(from => $cgi);
        if (! scalar @froms) {
            die "set_ops requires a \"from\" parameter.";
        } else {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir, \@froms);
            # Convert the IDs to results.
            $result = [map { [$_] } @$idList];
        }
    } elsif ($request eq 'amr_genomes') {
        ($oh, $label) = ComputeOutputFile(set => $cgi, $sessionDir);
        my $constraintList = ComputeConstraints($cgi);
        # Insure we have a from set.
        my @froms = GetNames(from => $cgi);
        if (! scalar @froms) {
            die "amr_genomes requires a \"from\" parameter.";
        } else {
            # Get the IDs to use.
            my $idList = ComputeInputIds($cgi, $sessionDir, \@froms);
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
        my ($name) = GetNames(from => $cgi, 1);
        open(my $ih, "<$sessionDir/$name.table") || die "Could not access table $name: $!";
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            my @fields = split /\t/, $line;
            push @$result, \@fields;
        }
    } elsif ($request eq 'describe_set') {
        my ($name) = GetNames(from => $cgi, 1);
        $result = [[ DescribeItem(set => $name, $sessionDir) ]];
    } elsif ($request eq 'describe_table') {
        my ($name) = GetNames(from => $cgi, 1);
        $result = [[ DescribeItem(table => $name, $sessionDir) ]];
    } elsif ($request eq 'clear') {
        my $tbls = ClearWorkspace(table => $sessionDir);
        my $sets = ClearWorkspace(set => $sessionDir);
        $result = [[ ucfirst(CountString($tbls, 'table', 'tables')) . " and " . CountString($sets, 'set', 'sets') . " deleted." ]];
    } elsif ($request eq 'clear_sets') {
        my $sets = ClearWorkspace(set => $sessionDir);
        $result = [[ ucfirst(CountString($sets, 'set', 'sets')) . " deleted." ]];
    } elsif ($request eq 'clear_tables') {
        my $tbls = ClearWorkspace(table => $sessionDir);
        $result = [[ ucfirst(CountString($tbls, 'table', 'tables')) . " deleted." ]];
    } elsif ($request eq "delete_tables") {
        my @tables = GetNames(from => $cgi);
        my $tbls = DeleteItems(table => \@tables, $sessionDir);
        $result = [[ ucfirst(CountString($tbls, 'table', 'tables')) . " deleted." ]];
    } elsif ($request eq "delete_sets") {
        my @sets = GetNames(from => $cgi);
        my $sets = DeleteItems(set => \@sets, $sessionDir);
        $result = [[ ucfirst(CountString($sets, 'set', 'sets')) . " deleted." ]];
    } elsif ($request eq 'define') {
        require SeedUtils;
        my $definitionsH = SeedUtils::read_encoded_object("$FIG_Config::web_dir/lib/intents.json");
        my $term = $cgi->param('intent');
        if (! $term) {
            die "No term specified for define.";
        } else {
            # Note we trim leading spaces.
            my $definition = $definitionsH->{$term} // "I do not understand $term.";
            $definition =~ s/^\s+//;
            print "$definition\n";
        }
    } elsif ($request eq 'show_peg') {
        # Compute the input set and the position of the desired peg.
        my $set = GetNames(from => $cgi, 1);
        my $position = $cgi->param('position') || die "No set position specified.";
        # Extract the desired peg.
        my $selectedPeg = LocateId($sessionDir, $set, $position);
        # Display it in the browser.
        DisplayFeature($selectedPeg, $acct);
    } else {
        die "Invalid request $request.\n";
    }
    if (scalar @$result) {
        PrintResult($oh, $result);
    }
    # Insure there is some output if we spooled the results to a file.
    if ($oh) {
        $label ||= "Result set produced with no label.";
        print "$label\n";
        my $lines = scalar(@$result) - $headers;
        print CountString($lines, 'line', 'lines') . " output.\n";
    }
    # Check for job status.
    if ($checkJobs) {
        my $jobList = Job::Check($sessionDir);
        if (scalar @$jobList) {
            print join("\n", @$jobList, "");
        }
    }
};
if ($@) {
    print "ERROR: $@\n";
}

# Erase the workspace, returning a count of the items deleted.
sub ClearWorkspace {
    my ($type, $sessionDir) = @_;
    # The output count will go in here.
    my $retVal = 0;
    # Get the files in the workspace.
    opendir(my $dh, $sessionDir) || die "Could not open session directory: $!";
    my @files = grep { $_ =~ /^[A-Za-z]\w*\.(\w+)/ } readdir $dh;
    # Loop through them.
    for my $file (@files) {
        # Get the file type and optional suffix.
        my ($fname, $ftype, $suffix) = split /\./, $file, 3;
        # Only proceed if it's the proper type.
        if ($ftype eq $type) {
            # Delete the file.
            unlink "$sessionDir/$file";
            # Count it if it's the base file.
            $retVal++ if (! $suffix);
        }
    }
    # Return the delete count.
    return $retVal;
}

# Delete one or more result sets, returning a count.
sub DeleteItems {
    my ($type, $list, $sessionDir) = @_;
    my $retVal = 0;
    for my $item (@$list) {
        my $itemName = "$sessionDir/$item.$type";
        if (-f $itemName) {
            unlink $itemName;
            unlink "$itemName.label";
            $retVal++;
        }
    }
    # Return the count.
    return $retVal;
}

# Display a count. The singular or plural is chosen.
sub CountString {
    my ($count, $singular, $plural) = @_;
    my $retVal;
    if ($count == 0) {
        $retVal = "no $plural";
    } elsif ($count == 1) {
        $retVal = "$count $singular";
    } else {
        $retVal = "$count $plural";
    }
    return $retVal;
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
    my ($type, $cgi, $sessionDir, $displayList) = @_;
    # These will be the return outut handle and label.
    my ($retVal, $label);
    # Get the set/table name.
    my $name = $cgi->param('save');
    # Only proceed if we have a name.
    if ($name) {
        # Compute the display name.
        my $display = ucfirst $type . ' ' . $name;
        # Compute the label to use.
        $label = ComputeLabel($cgi, $displayList);
        # Suffix the type to the file name.
        $name .= ".$type";
        # Open the file for output.
        open($retVal, ">$sessionDir/$name") || die "Could not open output $type: $!";
        # Create the label.
        open(my $oh, ">$sessionDir/$name.lbl") || die "Could not open label file for $name: $!";
        print $oh "$label\n";
        $label = "$display now contains $label.";
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
        # Only process non-null constraints.
        if ($constraint) {
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
    }
    # Return the constraint list.
    return \@retVal;
}

# Return the list of fields to display.
sub ComputeFields {
    my ($objectType => $cgi) = @_;
    my $fieldMap = FIELD_NAME_TO_PATRIC->{$objectType};
    my $line = $cgi->param('display');
    my @fields = split /,/, $line;
    my @retVal;
    for my $field (@fields) {
        my $name = $fieldMap->{lc $field};
        if (! $name) {
            die "Invalid display field name $field.";
        } else {
            push @retVal, $name;
        }
    }
    return \@retVal;
}

# Return a list of the IDs to use in selecting objects. This involves parsing the FROM and NOT
# parameters. Note we can pass in the from list optionally.
sub ComputeInputIds {
    my ($cgi, $sessionDir, $froms) = @_;
    # This will be the output ID list.
    my @retVal;
    # Create a hash of the NOT values.
    my %notIDs;
    # Get the list of NOT sets.
    my @notSets = GetNames('not' => $cgi);
    # Loop through them, filling the hash.
    for my $notSet (@notSets) {
        if ($notSet) {
            my $notFile = "$sessionDir/$notSet.set";
            open(my $ih, "<$notFile") || die "Could not open ID exclusion set $notSet: $!";
            while (! eof $ih) {
                my $line = <$ih>;
                chomp $line;
                $notIDs{$line} = 1;
            }
        }
    }
    # Now loop through the FROM sets, filling the output.
    my @fromSets;
    if ($froms) {
        @fromSets = @$froms;
    } else {
        @fromSets = GetNames(from => $cgi);
    }
    for my $fromSet (@fromSets) {
        if ($fromSet) {
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

# Compute the label to use for an output set.
sub ComputeLabel {
    my ($cgi, $displayList) = @_;
    # This will be the return value.
    my $retVal = 'an unknown result set';
    # Get the request type. This is the most important thing.
    my $request = $cgi->param('request');
    # Only proceed if the request is valid.
    if ($request) {
        # Determine the output object type.
        my $type = OBJECT_TYPE->{$request};
        my $fieldMap = FIELD_NAME->{$type};
        # Do we have display fields?
        my $tableFields;
        if (RETURNS_TABLE->{$request}) {
            # Get the display fields.
            my @fnames = map { $fieldMap->{$_} } @$displayList;
            $tableFields = 'the ' . CommaSplice(@fnames);
        }
        # Compute the source.
        my $sourceString;
        my @froms = GetNames(from => $cgi);
        my @nots = GetNames('not' => $cgi);
        my $pick = $cgi->param('pick');
        if (! @froms) {
            $sourceString = "all $type";
        } else {
            if ($pick) {
                $sourceString = "$pick $type in ";
            } else {
                $sourceString = "$type in ";
            }
            $sourceString .= CommaSplice(@froms);
            if (@nots) {
                $sourceString .= ' but not in ' . CommaSplice(@nots);
            }
        }
        # If we have display fields, insure we have a proper connector.
        if ($tableFields) {
            $sourceString = "from $sourceString";
        }
        # Compute the filters.
        my $filters;
        my @constraints = grep { $_ } $cgi->param('constraint');
        if (@constraints) {
            my @filters;
            for my $constraint (@constraints) {
                my $filter;
                my ($type, $field, $value) = split /,/, $constraint;
                if ($type eq 'susceptible' || $type eq 'resistant') {
                    $field = 'any drug' if ($field eq '*');
                    $filter = "are $type to $field";
                } else {
                    $field = $fieldMap->{$field};
                    if ($type eq 'exclude') {
                        $filter = "do not have the $field $value";
                    } else {
                        $filter = "have the $field $value";
                    }
                }
                push @filters, $filter;
            }
            $filters = 'that ' . CommaSplice(@filters);
        }
        my @sequence = grep { $_ } ($tableFields, $sourceString, $filters);
        $retVal = join(' ', @sequence);
    }
    # Return the label.
    return $retVal;
}

# Comma-splice a list of words together.
sub CommaSplice {
    my (@words) = @_;
    my $retVal;
    my $count = scalar @words;
    if ($count == 1) {
        $retVal = $words[0];
    } elsif ($count == 2) {
        $retVal = $words[0] . ' and ' . $words[1];
    } else {
        my ($last) = pop @words;
        $retVal = join(', ', @words, "and $last");
    }
    return $retVal;
}

# Extract a single record from a set.
sub LocateId {
    my ($sessionDir, $set, $position) = @_;
    # Open the set.
    open(my $ih, "<$sessionDir/$set.set") || die "Could not open set $set: $!";
    my $retVal;
    while (! eof $ih && $position > 0) {
        my $line = <$ih>;
        if ($position == 1) {
            chomp $line;
            $retVal = $line;
        }
        $position--;
    }
    # Insure we found something.
    if (! $retVal) {
        die "Position $position not valid for set $set.";
    }
    # Return the ID.
    return $retVal;
}

# Display a feature for the specified account.
sub DisplayFeature {
    my ($peg, $account) = @_;
    my $ua = LWP::UserAgent->new();
    my $url = "http://p3.theseed.org/qa/events/notify/alexa?type=navigate&data=$peg";
    my $response = $ua->get($url);
    if ($response->is_success) {
        print "Feature $peg selected.\n";
    } else {
        die "Error " . $response->code . " in feature $peg request: " . $response->content;
    }
}

# Retrieve the set of FROM or NOT names. If $max is TRUE, then exactly that number of values must be specified.
sub GetNames {
    my ($parm, $cgi, $max) = @_;
    my @names = grep { $_ } $cgi->param($parm);
    my @retVal;
    for my $name (@names) {
        my $realName = substr(uc $name, 0, 1);
        push @retVal, $realName;
    }
    if ($max && scalar(@retVal) != $max) {
        my $valueWord = ($max == 1 ? 'value' : 'values');
        die "Exactly $max \"$parm\" $valueWord must be specified.";
    }
    return @retVal;
}
