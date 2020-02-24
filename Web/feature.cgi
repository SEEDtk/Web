#!/usr/bin/env perl

use strict;
use CGI;
use lib 'lib';
use WebUtils;
use Web_Config;
use Env;
use File::Spec;
use GenomeTypeObject;


=head1 Feature Display Script

This script makes a primitive display of a feature in a GTO.  The parameters are as follows:

=over 4

=item gto

The path to the GTO file for the genome.

=item fid

The ID of the feature to display.

=back

=cut

my $cgi = CGI->new();
my $fid = $cgi->param("fid");
print $cgi->header();
print $cgi->start_html(-title => "$fid");
eval {
    my $gtoName = $cgi->param("gto");
    my $gto = GenomeTypeObject->create_from_file("$FIG_Config::data/$gtoName.gto");
    my $featList = $gto->{features};
    my $i = 0;
    while ($i < scalar @$featList && $featList->[$i]{id} ne $fid) {
        $i++;
    }
    my $feature = $featList->[$i];
    if (! $feature) {
        print "<h2>$fid not found!</h2>\n";
    } else {
        print "<h1>$fid $feature->{function}</h1>\n";
        my $annoList = $feature->{annotations};
        if ($annoList) {
            print "<h2>Annotation History</h2>\n";
            print "<ul>\n";
            for my $annotation (@$annoList) {
                print "<li>$annotation->[0]</li>\n";
            }
            print "</ul>\n";
        }
        my $locs = $feature->{location};
        if ($locs) {
            print "<h2>Location</h2>\n";
            print "<ol>\n";
            for my $loc (@$locs) {
                print "<li>$loc->[0]_$loc->[1]$loc->[2]$loc->[3]</li>\n";
            }
            print "</ol>\n";
        }
        my $prot = $feature->{protein_translation};
        if ($prot) {
            print "<h2>Protein Translation</h2>";
            print "<pre>$prot</pre>\n";
        }
    }
};
if ($@) {
    print "<h2>Error: $@</h2>\n";
}
print $cgi->end_html();
