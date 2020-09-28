#!/usr/bin/env perl

=head1 Family Pair CGI Script

This script takes as input a pair of protein family IDs.  It reads through the pair file C<couples.tbl>
and produces a display of the feature pairs that represent the coupled protein family pair.

The parameters are:

=over 4

=item f1

ID of the first protein family

=item f2

ID of the second protein family

=back

=cut

use strict;
use lib 'lib';
use CGI;
use TestUtils;
use WebUtils;
use XML::Simple;
use Web_Config;
use SeedUtils;

use constant PATRIC_PREFIX_URL => "https://www.patricbrc.org/view/Feature/";
use constant CORE_PREFIX_URL => "https://core.theseed.org/FIG/seedviewer.cgi?page=Annotation&feature=";

my $cgi = CGI->new();
my $f1 = $cgi->param('f1');
my $f2 = $cgi->param('f2');
if ($f1 gt $f2) {
    ($f1, $f2) = ($f2, $f1);
}
print CGI::header();
my $title = "Coupled Pairs for $f1 and $f2";
print CGI::start_html(-title => $title, -style =>  { src => "css/Basic.css" });
eval {
    print CGI::h1($title) . "\n";
    open(my $ih, '<', "$FIG_Config::data/GTOcouple/genomes.tbl") || die "Could not open genomes.tbl: $!";
    # Get a hash of genome names.
    my %genomes;
    while (! eof $ih) {
        my $line = <$ih>;
        my ($id, $name) = split /\t/, $line;
        $genomes{$id} = $name;
    }
    close $ih; undef $ih;
    open($ih, '<', "$FIG_Config::data/GTOcouple/couples.tbl") || die "Could not open couples.tbl: $!";
    print CGI::start_div({ id => "Pod" }) . "\n";
    my $couples;
    # Skip the header.
    my $line = <$ih>;
    # Find the pairing.
    while (! eof $ih && ! $couples) {
        $line = <$ih>;
        chomp $line;
        my ($fam1, $name1, $fam2, $name2, $pairs) = split /\t/, $line;
        if ($fam1 eq $f1 && $fam2 eq $f2) {
            print CGI::p("$f1 role: $name1") . "\n";
            print CGI::p("$f2 role: $name2") . "\n";
            $couples = [ split /,/, $pairs];
            print CGI::p(scalar(@$couples) . " couplings found for this family pair.") . "\n";
            print CGI::start_table();
            print CGI::Tr(CGI::th($f1), CGI::th($f2), CGI::th("Genome")) . "\n";
            $couples = $pairs;
        }
    }
    close $ih; undef $ih;
    if (! $couples) {
        print CGI::end_div() . "\n";
        die "Specifing pairing not found.";
    } else {
        for my $pair (split /,/, $couples) {
            my ($fid1, $fid2) = split /:/, $pair;
            my $gName = $genomes{SeedUtils::genome_of($fid1)};
            print CGI::Tr(CGI::td(fid_link($fid1)), CGI::td(fid_link($fid2)), CGI::td($gName)) . "\n";
        }
        print CGI::end_table();
        print CGI::end_div() . "\n";
    }
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();

sub fid_link {
    my ($fid) = @_;
    my $genome = SeedUtils::genome_of($fid);
    return CGI::a({ href => "coupling.cgi?genome=$genome&peg=$fid"}, $fid);
}
