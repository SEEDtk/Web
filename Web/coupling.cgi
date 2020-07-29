#!/usr/bin/env perl

=head1 Coupling CGI Script

This script takes as input a genome ID and a focus peg.  It provides links to other pegs coupled to the original.

The parameters are:

=over 4

=item genome

ID of the genome of interest.  It must have a GTO in the "GTOcouple" subdirectory of the SEEDtk data directory.

=item peg

Feature to display.  If omitted, the whole genome is displayed.

=item path (only used if "peg" is specified)

The features displayed on the way here.

=item filter

Minimum coupling size value.  The default is C<0>.

=item focus

For the genome page, the ID of the last peg displayed

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

my ($home, $newPath, $path, $urlPrefix);
my $cgi = CGI->new();
my $genome = $cgi->param('genome');
my $pegId = $cgi->param('peg');
my $filter = $cgi->param('filter') // 0;
print CGI::header();
my $title = ($pegId ? "Feature Coupling for $pegId" : ($genome ? "Peg List for $genome" : "Genomes With Coupling"));
print CGI::start_html(-title => $title, -style =>  { src => "css/Basic.css" });
eval {
    # Parse the path.
    $path = $cgi->param('path') // "";
    $newPath = "";
    # Read in the GTO.
    $genome = $cgi->param('genome');
    if (! $genome) {
        list_genomes();
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
                display_genome($gto);
            } else {
                display_peg($gto);
            }
        }
    }
    print "\n";
    print '<script>';
    print 'document.getElementById("focus").focus()';
    print '</script>';
    print "\n";
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();

sub display_peg {
    my ($gto) = @_;
    # Here we are focused on a single feature.  We show the feature's couplings, and a short history of
    # previous features viewed.
    my @path = split /,/, $path;
    shift @path if (scalar @path > 10);
    $newPath = join(",", @path, $pegId);
    my $focus = $gto->find_feature($pegId);
    print CGI::h1("$pegId $focus->{function}") . "\n";
    print CGI::start_div({ id => "Pod" }) . "\n";
    print CGI::p(CGI::a({ href => "coupling.cgi?genome=$genome&filter=$filter&focus=$pegId" }, "Return to genome page.")) . "\n";
    filter_form();
    # Get all the features related to the focus feature and find the subsystems.
    my $couplings = $focus->{couplings} // [];
    my @fids = ($pegId, map { $_->[0] } @$couplings);
    my $subHash = get_subsystems($gto, \@fids);
    # Now we need to build a table of the coupled features.
    print CGI::h2("Couplings") . "\n";
    print CGI::start_table() . "\n";
    print CGI::Tr(CGI::th("Feature"), CGI::th("Home"), CGI::th("Function"), CGI::th("Score"),
            CGI::th("Strength"), CGI::th("Others"), CGI::th("Subsystems")) . "\n";
    print CGI::Tr(fid_info($pegId, $focus->{function}, 1), CGI::td({ class => 'num' }, 'focus'),
            CGI::td("&nbsp;"), CGI::td("&nbsp;"),
            CGI::td($subHash->{$pegId}));
    my $hidden = 0;
    for my $coupling (@$couplings) {
        my ($fid, $score, $strength) = @$coupling;
        if ($score < $filter) {
            $hidden++;
        } else {
            my $other = $gto->find_feature($fid);
            print CGI::Tr(fid_info($fid, $other->{function}),
                    CGI::td({ class => 'num' }, $score), CGI::td({ class => 'num'}, $strength),
                    CGI::td(others_link($focus, $other)),
                    CGI::td($subHash->{$fid})) . "\n";
        }
    }
    print CGI::end_table() . "\n";
    if ($hidden > 0) {
        print CGI::p("$hidden couplings hidden by score filter.") . "\n";
    }
    if (scalar @path) {
        print CGI::h2("History") . "\n";
        print CGI::start_table() . "\n";
        print CGI::Tr(CGI::th("Feature"), CGI::th("Home"), CGI::th("Function")) . "\n";
        for my $fid (@path) {
            my $function = $gto->feature_function($fid);
            print CGI::Tr(fid_info($fid, $function)) . "\n";
        }
        print CGI::end_table() . "\n";
    }
    print CGI::end_div() . "\n";
}

sub others_link {
    my ($feat1, $feat2) = @_;
    my $retVal = "&nbsp;";
    my $fam1 = pgfam($feat1);
    my $fam2 = pgfam($feat2);
    if ($fam1 && $fam2) {
        $retVal = CGI::a({ href => "familyPair.cgi?f1=$fam1&f2=$fam2", target => "_blank" }, "PAIRS");
    }
}

sub pgfam {
    my ($feat) = @_;
    my $retVal = "0";
    my $families = $feat->{family_assignments} // [];
    for my $family (@$families) {
        if ($family->[0] eq 'PGFAM') {
            $retVal = $family->[1];
        }
    }
    return $retVal;
}

sub display_genome {
    my ($gto) = @_;
    # Here we are displaying the whole genome.  We show only the features with couplings
    # that pass the filter.
    my $focus = $cgi->param("focus") // "";
    print CGI::h1("Genome $genome $gto->{scientific_name}") . "\n";
    print CGI::start_div({ id => "Pod" }) . "\n";
    print CGI::p(CGI::a({ href => "coupling.cgi"}, "Return to main page.")) . "\n";
    filter_form();
    print CGI::input({ type => 'hidden', name => 'genome', value => $genome }) . "\n";
    my @feats = sort { SeedUtils::by_fig_id($a->{id}, $b->{id}) }
            grep { has_couplings($_) } @{$gto->{features}};
    my $count = scalar @feats;
    my $subHash = get_subsystems($gto, [map { $_->{id} } @feats]);
    print CGI::h2("$count Features with Couplings") . "\n";
    print CGI::start_table() . "\n";
    print CGI::Tr(CGI::th("Feature"), CGI::th("Home"), CGI::th("Function"), CGI::th("Subsystems")) . "\n";
    for my $feat (@feats) {
        my $fid = $feat->{id};
        print CGI::Tr(fid_info($fid, $feat->{function}, ($fid eq $focus)), CGI::td($subHash->{$fid})) . "\n";
    }
    print CGI::end_table() . "\n";
    print CGI::end_div() . "\n";
}

sub list_genomes {
    # Here we create a table of all the available genomes.
    print CGI::h1("Genomes with Coupling Data") . "\n";
    print CGI::start_div({ id => "Pod" }) . "\n";
    open(my $ih, '<', "$FIG_Config::data/GTOcouple/genomes.tbl") || die "Could not open genomes.tbl file: $!";
    my @genomes;
    while (! eof $ih) {
        my $line = <$ih>;
        chomp $line;
        push @genomes, [split /\t/, $line];
    }
    @genomes = sort { $a->[1] cmp $b->[1] } @genomes;
    print CGI::start_table() . "\n";
    print CGI::Tr(CGI::th("Genome"), CGI::th("Scientific Name"), CGI::th({ class => 'num' }, "Couplings")) . "\n";
    for my $genomeData (@genomes) {
        my ($id, $name, $count) = @$genomeData;
        print CGI::Tr(CGI::td(CGI::a({ href => "coupling.cgi?genome=$id" }, $id)),
                CGI::td($name), CGI::td({ class => 'num' }, $count)) . "\n";
    }
    print CGI::end_table() . "\n";
    print CGI::end_div() . "\n";
}

sub fid_info {
    my ($fid, $function, $focusFlag) = @_;
    my %aParms = (href => "coupling.cgi?genome=$genome&peg=$fid&filter=$filter&path=$newPath");
    if ($focusFlag) {
        $aParms{id} = "focus";
    }
    return CGI::td(CGI::a(\%aParms, $fid)),
           CGI::td(CGI::a({ href => "$urlPrefix$fid", target => "_blank" }, $home)), CGI::td($function);
}

sub has_couplings {
    my ($feat) = @_;
    my $couples = get_couplings($feat);
    return scalar(@$couples) > 0;
}

sub get_couplings {
    my ($feat) = @_;
    my $couples = $feat->{couplings} // [];
    my @retVal = grep { $_->[1] >= $filter } @$couples;
    return \@retVal;
}

sub filter_form {
    print CGI::start_form({ action => "coupling.cgi", method => "GET" }) . "\n";
    print CGI::start_table() . "\n";
    print CGI::Tr(CGI::td("Minimum Score"), CGI::td(CGI::input({ type => 'text', name => 'filter', value => $filter})),
            CGI::td(CGI::input({ type => 'submit', value => 'REFRESH' }))) . "\n";
    print CGI::end_table() . "\n";
    print CGI::input({ type => 'hidden', name => 'genome', value => $genome }) . "\n";
    if ($pegId) {
        print CGI::input({ type => 'hidden', name => 'peg', value => $pegId }) . "\n";
    }
    if ($path) {
        print CGI::input({ type => 'hidden', name => 'path', value => $path }) . "\n";
    }
    print CGI::end_form();
}

# Here we want to find the subsystems containing each of the features in the incoming list.
sub get_subsystems {
    my ($gto, $featList) = @_;
    # Initialize to every feature having no subsystems.
    my %retVal = map { $_ => [] } @$featList;
    my $subsystems = $gto->{subsystems} // [];
    for my $subsystem (@$subsystems) {
        my $name = $subsystem->{name};
        my $subID = $name;
        $subID =~ tr/ /_/;
        my $link = "https://core.theseed.org/FIG/seedviewer.cgi?page=Subsystems;subsystem=$subID";
        my $bindings = $subsystem->{role_bindings} // [];
        for my $binding (@$bindings) {
            for my $fid (@{$binding->{features}}) {
                if ($retVal{$fid}) {
                    push @{$retVal{$fid}}, CGI::a({ href => $link, target => "_blank" }, $name);
                }
            }
        }
    }
    # Run through the hash and convert each list to a string.
    for my $fid (keys %retVal) {
        my @subs = @{$retVal{$fid}};
        my $html = "<em>**</em>";
        if (scalar @subs) {
            $html = join(" | ", @subs);
        }
        $retVal{$fid} = $html;
    }
    return \%retVal;
}

1;
