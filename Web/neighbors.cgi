#!/usr/bin/env perl

use strict;
use CGI;
use lib 'lib';
use WebUtils;
use Web_Config;
use Env;
use P3DataAPI;
use P3Utils;
use RoleParse;
use RepGenomeDb;
use RepGenome;
use Template;
use File::Spec;

=head1 Find the Neighborhood of a Genome

This script will find the genomes believed to be in the neighborhood of another genome using the data in a representative-genomes
directory. The output will contain the neighboring genomes and their similarity scores compared to the original.

=head2 Parameters

The CGI parameters are the following.

=over 4

=item repDir

The representative-genomes directory to use for the search. This directory must have the files described in L<RepGenomeDb/new_from_dir>.

=item genome

The ID of the genome whose neighborhood is desired.

=item size

The desired size of the neighborhood. The default is C<100>.

=item minScore

The minimum similarity score for a representative genome for its represented set to be considered close. The default is C<25>.

=item sliceSize

The number of genomes to take from each representative set. The default is C<35>.

=back

=cut


# Write the CGI header.
my $cgi = CGI->new();
print $cgi->header();
eval {
    # Get the parameters.
    my $repDir = $cgi->param('repDir');
    my $genomeID = $cgi->param('genome');
    my $size = $cgi->param('size') // 100;
    my $sliceSize = $cgi->param('sliceSize') // 30;
    my $minScore = $cgi->param('minScore') // 25;
    # Compute the full repDir.
    $repDir = File::Spec->catpath('', $FIG_Config::data, $repDir);
    # Check the main parameters.
    if (! $repDir) {
        die "No representative-genome directory specified.";
    } elsif (! -d $repDir) {
        die "Representative-genome directory $repDir is missing or invalid.";
    } elsif (! $genomeID) {
        die "No input genome ID specified.";
    }
    # Get access to PATRIC.
    my $p3 = P3DataAPI->new();
    # The template data will go in here.
    my %vars = (genome_id => $genomeID);
    # Get the seed protein of the input genome.
    my $seedHash = FindSeeds($p3, [$genomeID]);
    my $gData = $seedHash->{$genomeID};
    if (! $gData) {
        die "No seed protein found in $genomeID.";
    }
    my ($gProt, $genome_name) = @$gData;
    $vars{genome_name} = $genome_name;
    my $repDB = RepGenomeDb->new_from_dir($repDir);
    # Find the best representative.
    my ($rep_id, $rep_score) = $repDB->find_rep($gProt);
    my $rep_name;
    if ($rep_id) {
        my $repObject = $repDB->rep_object($rep_id);
        $rep_name = $repObject->name;
    } else {
        die "No representative genome found for $genomeID.";
    }
    $vars{rep_id} = $rep_id;
    $vars{rep_score} = $rep_score;
    $vars{rep_name} = $rep_name;
    # Find the neighbors.
    my $neighbors = $repDB->FindRegion($gProt, size => $size, sliceSize => $sliceSize, minScore => $minScore);
    # Get their seed proteins.
    $seedHash = FindSeeds($p3, $neighbors);
    # Create a rep-genome object for the main protein.
    my $repObject = RepGenome->new($genomeID, prot => $gProt, K => $repDB->K);
    # Get the similarities for the other genomes.
    my @genomes;
    for my $other (@$neighbors) {
        my $oData = $seedHash->{$other};
        die "No protein found for $other." if ! $oData;
        my ($prot, $name) = @$oData;
        my $score = $repObject->check_genome($prot);
        push @genomes, { score => $score, name => $name, id => $other };
    }
    $vars{genomes} = [ sort { $b->{score} <=> $a->{score} } @genomes];
    # Create the web page.
    my $templateEngine = Template->new(ABSOLUTE => 1);
    $templateEngine->process('css/neighbors.tt', \%vars) || die $templateEngine->error();
};
if ($@) {
    print "<html><body><h1>SCRIPT ERROR</h1><p>$@</p></body></html>\n";
}


## Get the seed proteins and names of the listed genomes. Returns a hash ref.
sub FindSeeds {
    my ($p3, $genomes) = @_;
    # Get all the features that look promising.
    my $results = P3Utils::get_data_keyed($p3, feature => [['eq', 'product', 'Phenylalanyl-tRNA synthetase alpha chain']],
            ['genome_id', 'product', 'genome_name', 'aa_sequence'], $genomes, 'genome_id');
    # The ones we keep go in here.
    my %retVal;
    # Loop through the results.
    for my $genomeDatum (@$results) {
        my ($id, $function, $name, $prot) = @$genomeDatum;
        my $checksum = RoleParse::Checksum($function);
        if ($checksum eq 'WCzieTC/aZ6262l19bwqgw') {
            $retVal{$id} = [$prot, $name];
        }
    }
    # Return the proteins found.
    return \%retVal;
}
