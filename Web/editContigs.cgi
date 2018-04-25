#!/usr/bin/env perl

use strict;
use CGI;
use Pod::Simple::HTML;
use lib 'lib';
use WebUtils;
use Web_Config;
use Env;
use File::Spec;
use File::Basename;
use File::Copy::Recursive;
use GenomeTypeObject;

=head1 Create a FASTA File With Contigs Removed

This script takes as input a L<GenomeTypeObject> file and creates a FASTA file with the selected contigs removed.
The following CGI parameters are expected.

=over 4

=item delete_contig

This is multi-valued, and contains the IDs of the contigs to delete.

=item gtoFile

The name of the input GTO file.

=item account

The name to give to the FASTA file. The file will be put in the web space directory, so you can specify a relative
directory path as part of the file name.

=back

=cut

# Get the CGI query object.
my $cgi = CGI->new();
# Write a header.
print CGI::header('text/html');
print "<head><title>Genome Contig Pruning</title></head>\n";
print "<body>\n";
eval {
    my $outFile = $cgi->param('account');
    if (! $outFile) {
        die "No output file name specified.";
    } else {
        $outFile = File::Spec->catfile($FIG_Config::data, 'WebSpaces', $outFile);
        my $outDir = dirname($outFile);
        if (! -d $outDir) {
            # Insure we have our output directory.
            File::Copy::Recursive::pathmk($outDir);
        }
        # Now we have a place for the output file. Read the input file.
        my $inFile = $cgi->param('gtoFile');
        if (! $inFile) {
            die "No GTO file specified.";
        } elsif (! -s $inFile) {
            die "GTO file $inFile not found or invalid.";
        }
        my $gto = GenomeTypeObject->create_from_file($inFile);
        # Now get the list of contigs to delete.
        my %badContigs = map { $_ => 1 } $cgi->multi_param('delete_contig');
        # Open the output file.
        open(my $oh, ">$outFile") || die "Could not create $outFile: $!";
        my ($count, $deleted) = (0, 0);
        # Loop through the contigs.
        for my $contig (@{$gto->{contigs}}) {
            my $id = $contig->{id};
            if (! $badContigs{$id}) {
                print $oh ">$id\n$contig->{dna}\n";
                $count++;
            } else {
                $deleted++;
            }
        }
        close $oh;
        print CGI::p("$count contigs written to $outFile. $deleted removed.") . "\n";
    }
};
if ($@) {
    print CGI::blockquote("ERROR: $@");
}
print "</body></html>\n";
