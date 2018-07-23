#!/usr/bin/env perl

use strict;
use CGI;
use lib 'lib';
use WebUtils;
use Web_Config;
use Env;
use EvalHelper;

=head1 Evaluate a Genome

This script will evaluate a single genome and output a web page for it. All the work is done by L<EvalHelper>.

=head2 Parameters

The CGI parameters are the following.

=over 4

=item genome

The ID of the genome whose evaluation is desired.

=back

=cut


# Write the CGI header.
my $cgi = CGI->new();
print $cgi->header();
eval {
    # Get the parameters.
    my $genomeID = $cgi->param('genome');
    my $html = EvalHelper::Process($genomeID, deep => 1);
    print $html;
};
if ($@) {
    print "<html><body><h1>SCRIPT ERROR</h1><p>$@</p></body></html>\n";
}

