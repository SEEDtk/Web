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
    my $ssName = ssName($ssID);
    # We need to read the subsystem spreadsheet and then the assigned_functions file for each genome.
    # This will contain a list of the roles in each column.
    my @roles;
    # This will contain the role abbreviations.
    my @abbrs;
    # This will contain the role strings.
    my @names;
    # This will map roles to column indices.
    my %columns;
    # For each role, this will contain a hash mapping incorrect roles to pegs containing them.
    my @countHashes;
    # For each role, this will count the number of times it occurs correctly in a feature.
    my @correctRole;
    # For each role, this will count the pegs that are disconnected.
    my @disPegs;
    # This will hold the HTML for the spreadsheet table.
    my @lines;
    # This will hold the IDs of the missing genomes.
    my @missingGenomes;
    # Write the title and link to the subsystem page.
    print CGI::h1(CGI::a({ href => (CORE_SUBSYSTEM_URL . $ssID), target => "_blank"}, $ssName));
    # Read the subsystem roles.
    open(my $sh, '<', "$ssDir/$ssID/spreadsheet") || die "Could not open subsystem spreadsheet: $!";
    for (my $line = <$sh>; defined $line && $line ne SECTION_MARKER; $line = <$sh>) {
        chomp $line;
        my ($abbr, $function) = split /\t/, $line;
        push @abbrs, $abbr;
        push @names, $function;
        my @funRoles = SeedUtils::roles_of_function($function);
        push @roles, \@funRoles;
        for my $role (@funRoles) {
            $columns{$role} = $#roles;
        }
        push @correctRole, 0;
        push @disPegs, 0;
        push @countHashes, { };
    }
    # Skip the groups.
    for (my $line = <$sh>; defined $line && $line ne SECTION_MARKER; $line = <$sh>) { }
    # Open the display section.
    print CGI::start_div({ id => 'Pod' });
    # Read the spreadsheet.  Each line is a genome.  We read the full spreadsheet into a hash
    # so the last version of a genome is kept.  Then we process them in order.
    my %rows;
    while (! eof $sh) {
        my $line = <$sh>;
        chomp $line;
        # Note that not all the role cells will be filled, so we need to fix that.
        my ($genome, $variant, @cells) = split /\t/, $line;
        while (scalar @cells < scalar @roles) {
            push @cells, '';
        }
        my $colsUsed = grep { $_ } @cells;
        if ($colsUsed) {
            $rows{$genome} = [$variant, @cells];
        }
    }
    # Write the spreadsheet header.
    push @lines, CGI::start_table();
    push @lines, CGI::Tr(CGI::th(['Genome', 'Variant', @abbrs]));
    # Now loop through the genomes.
    for my $genome (sort keys %rows) {
        my $row = $rows{$genome};
        my ($variant, @cells) = @$row;
        # This will hold the column index of each peg.
        my %pegCols;
        # Loop through the cells.  Each cell's peg list is converted to a hash:  peg -> mode.
        # The default mode is "missing".  We change the mode if the peg is found in the assigned
        # functions file.
        for (my $i = 0; $i < @cells; $i++) {
            my @pegs = split /,/, $cells[$i];
            my %cellH;
            for my $peg (@pegs) {
                if ($peg =~ /^\D/) {
                    $peg = "fig|$genome.$peg";
                } else {
                    $peg = "fig|$genome.peg.$peg";
                }
                $cellH{$peg} = 'missing';
                $pegCols{$peg}{$i} = 1;
            }
            $cells[$i] = \%cellH;
        }
        # Now get the assigned functions.  We have to put these in a hash because only the last one counts.
        my $functionH = read_functions($genome);
        if (! $functionH) {
            # Here the genome ID is not found.
            push @missingGenomes, $genome;
        } else {
            # Loop through the functions, looking for features and roles that matter.
            for my $peg (keys %$functionH) {
                my $function = $functionH->{$peg};
                my %runRoles = map { $_ => 1 } SeedUtils::roles_of_function($function);
                # This will be set to the columns that should contain this peg.
                my %goodCols;
                # This is a hash of the columns that do contain the peg.
                my $actualCols = $pegCols{$peg} // {};
                # Process each role individually.
                for my $role (keys %runRoles) {
                    my $colIdx = $columns{$role};
                    if (defined $colIdx) {
                        # NOTE we had to used "defined" because 0 is a valid column index.  Here the role is used by the spreadsheet.
                        # Verify that all roles in the column are present.
                        my $errors = grep { ! $runRoles{$_} } @{$roles[$colIdx]};
                        if (! $errors) {
                            # Here the peg belongs in the role's column.
                            $goodCols{$colIdx} = 1;
                        }
                    }
                }
                # Check the peg status.
                for my $goodCol (keys %goodCols) {
                    if ($actualCols->{$goodCol}) {
                        # Here the peg is in the correct column.
                        $cells[$goodCol]{$peg} = 'normal';
                        $correctRole[$goodCol]++;
                    } else {
                        # Here the peg is disconnected in this column.
                        $cells[$goodCol]{$peg} = 'disconnected';
                        $disPegs[$goodCol]++;
                    }
                }
                for my $actualCol (keys %$actualCols) {
                    if (! $goodCols{$actualCol}) {
                        # Here the peg is in a column where id does not belong.
                        $cells[$actualCol]{$peg} = 'bad';
                        push @{$countHashes[$actualCol]{$function}}, $peg;
                    }
                }
            }
            my $genomeLink = CGI::a({ href => (CORE_GENOME_URL . $genome), target => '_blank'}, $genome);
            my @cellLinks;
            for my $cell (@cells) {
                my $html = join("<br />", map { display_peg($_, $cell->{$_}) } sort keys %$cell) || '&nbsp;';
                push @cellLinks, $html;
            }
            push @lines, CGI::Tr(CGI::td([$genomeLink, $variant, @cellLinks]));
        }
    }
    push @lines, CGI::end_table();
    # Give the user a spreadsheet link.
    print CGI::p(CGI::a({ href => "#sheet" }, 'Go to spreadsheet'));
    # Are there missing genomes?
    if (scalar @missingGenomes) {
        my $count = scalar @missingGenomes;
        print CGI::p("$count genomes were not found.");
    }
    # Write the role table.
    write_role_table(\@names, \@abbrs, \@countHashes, \@correctRole, \@disPegs);
    # Write the spreadsheet.
    print CGI::h2(CGI::a({ name => 'sheet' }, "Subsystem Spreadsheet"));
    print CGI::p("LEGEND" . CGI::ul(
        CGI::li(CGI::a({ name => 'normal', class => 'normal' }, "Peg has correct role for column.")),
        CGI::li(CGI::a({ name => 'bad', class => 'bad' }, "Peg does not have correct role for column (Bad Role).")),
        CGI::li(CGI::a({ name => 'disconnected', class => 'disconnected' }, "Peg belongs in column, but is disconnected."))
        ));
    print join("\n", CGI::start_div({ class => 'wide' }), @lines, CGI::end_div());
    # Write the missing genome list.
    if (scalar @missingGenomes) {
        print CGI::h2("Genomes No Longer in SEED");
        print CGI::ol(CGI::li(\@missingGenomes));
    }
    print CGI::p((time - $start) . " seconds to compute and format page.");
    print CGI::end_div();
}

sub read_functions {
    my ($genome) = @_;
    my $retVal;
    my $funFile = "$orgDir/$genome/assigned_functions";
    if (-s $funFile) {
        open(my $ih, '<', $funFile) || die "Could not open assigned functions for $genome: $!";
        $retVal = {};
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            my ($id, $function) = split /\t/, $line;
            $retVal->{$id} = $function;
        }
    }
    return $retVal;
}

## Write the role table.  This tells us how many times each role is found and what other roles are found.
sub write_role_table {
    my ($roles, $abbrs, $countHashes, $correctRole, $badPegs, $disPegs) = @_;
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
