#!/usr/bin/env perl

use strict;
use CGI;

# Write the CGI header.
my $cgi = CGI->new();
print $cgi->header();
print $cgi->start_html();
print "<p>Hello</p>\n";
print $cgi->end_html();