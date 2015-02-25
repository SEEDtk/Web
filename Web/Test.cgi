#!/usr/bin/env perl

use strict;
use lib 'lib';
use CGI;
use TestUtils;
use WebUtils;
use XML::Simple;
use Web_Config;
use Shrub;		# This must go after "Web_Config" or it won't be found!

print CGI::header();
print CGI::start_html(-title => 'Test Page',
                      -style => { src => '/css/Basic.css' });

eval {
    # Get the script.
    my $cgi = CGI->new();
    my $struct = $cgi->param('structure');
    # Is this a file upload?
    if ($struct eq 'TBL File') {
        # Yes. Get the input file handle.
        my $ih = $cgi->upload('uploadFile');
        # Read in the file as a list of lists.
        my @table;
        while (! eof $ih) {
            my $line = <$ih>;
            chomp $line;
            push @table, [ split /\t/, $line ];
        }
        # Display the table as a matrix.
        print CGI::start_div({ id => 'Dump' });
        print TestUtils::Display(\@table, "Matrix");
        print CGI::end_div();
    } else {
        # Not an upload. Get the structure.
        my $retVal;
        if ($struct eq 'Shrub DBD') {
            $retVal = Shrub->new(offline => 1);
        } elsif ($struct eq 'Shrub Object') {
            $retVal = Shrub->new();
        } else {
            die "Unknown structure requested."
        }
        # Dump the result.
        print CGI::start_div({ id => 'Dump' });
        print TestUtils::Display($retVal, "Normal");
        print CGI::end_div();
    }
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();


1;
