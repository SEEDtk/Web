#!/usr/bin/env perl

=head1 Coupling CGI Script

This script takes as input a genome ID and a focus peg.  It provides links to other pegs coupled to the original.

The parameters are:

=over 4

=item genome

ID of the genome of interest.  It must have a GTO in the "GTOcouple" subdirectory of the SEEDtk data directory.

=item peg

Feature to display.

=item path

The features displayed on the way here.

=back

=cut

use strict;
use lib 'lib';
use CGI;
use TestUtils;
use WebUtils;
use XML::Simple;
use Web_Config;
use GenomeTypeObject;		# This must go after "Web_Config" or it won't be found!
use SeedUtils;

use constant PATRIC_PREFIX_URL => "https://www.patricbrc.org/view/Feature/";
use constant CORE_PREFIX_URL => "https://core.theseed.org/FIG/seedviewer.cgi?page=Annotation&feature=";

my ($home, $newPath, $urlPrefix);
my $cgi = CGI->new();
my $genome = $cgi->param('genome');
my $pegId = $cgi->param('peg');
print CGI::header();
my $title = ($pegId ? "Feature Coupling for $pegId" : "Peg List for $genome");
print CGI::start_html(-title => $title, -style =>  { src => "css/Basic.css" });
eval {
    # Parse the path.
    my $path = $cgi->param('path') // "";
    $newPath = "";
    # Read in the GTO.
    $genome = $cgi->param('genome');
    if (! $genome) {
        die "No genome ID specified.";
    } else {
        my $gtoFile = "$FIG_Config::data/GTOcouple/$genome.gto";
        if (! -s $gtoFile) {
            die "$genome not found in data directory.";
        } else {
            my $gto = GenomeTypeObject->create_from_file($gtoFile);
            # Compute the link style.
            $home = $gto->{home};
            $urlPrefix = PATRIC_PREFIX_URL;
            if ($home eq "CORE") {
                $urlPrefix = CORE_PREFIX_URL;
            }
            if (! $pegId) {
                print CGI::h1("Genome $genome $gto->{scientific_name}") . "\n";
                print CGI::start_div({ id => "Pod" }) . "\n";
                print CGI::p(CGI::a({ href => "coupling.html"}, "Return to coupling page."));
                print CGI::h2("Features with Couplings");
                print CGI::start_table() . "\n";
                print CGI::Tr(CGI::th("Feature"), CGI::th("Home"), CGI::th("Function")) . "\n";
                my @feats = sort { SeedUtils::by_fig_id($a->{id}, $b->{id}) }
                        grep { $_->{couplings} && @{$_->{couplings}} } @{$gto->{features}};
                for my $feat (@feats) {
                    print CGI::Tr(fid_info($feat->{id}, $feat->{function})) . "\n";
                }
                print CGI::end_table();
                print CGI::end_div();
            } else {
                my @path = split /,/, $path;
                shift @path if (scalar @path > 10);
                $newPath = join(",", @path, $pegId);
                my $focus = $gto->find_feature($pegId);
                print CGI::h1("$focus->{id} $focus->{function}") . "\n";
                print CGI::start_div({ id => "Pod" }) . "\n";
                print CGI::p(CGI::a({ href => "coupling.cgi?genome=$genome"}, "Return to genome page."));
                # Now we need to build a table of the coupled features.
                my $couplings = $focus->{couplings};
                print CGI::h2("Couplings") . "\n";
                print CGI::start_table() . "\n";
                print CGI::Tr(CGI::th("Feature"), CGI::th("Home"), CGI::th("Function"), CGI::th("Score"), CGI::th("Strength")) . "\n";
                for my $coupling (@$couplings) {
                    my ($fid, $score, $strength) = @$coupling;
                    my $function = $gto->feature_function($fid);
                    print CGI::Tr(fid_info($fid, $function),
                        CGI::td({ class => 'num' }, $score), CGI::td({ class => 'num'}, $strength)) . "\n";
                }
                print CGI::end_table() . "\n";
                print CGI::h2("History");
                print CGI::start_table() . "\n";
                print CGI::Tr(CGI::th("Feature"), CGI::th("Home"), CGI::th("Function")) . "\n";
                for my $fid (@path) {
                    my $function = $gto->feature_function($fid);
                    print CGI::Tr(fid_info($fid, $function)) . "\n";
                }
                print CGI::end_table();
                print CGI::end_div() . "\n";
            }
        }
    }
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();

sub fid_info {
    my ($fid, $function) = @_;
    return CGI::td(CGI::a({ href => "coupling.cgi?genome=$genome&peg=$fid&path=$newPath"}, $fid)),
           CGI::td(CGI::a({ href => "$urlPrefix$fid", target => "_blank" }, $home)), CGI::td($function);
}

1;
