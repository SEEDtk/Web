#!/usr/bin/env perl

#
# Copyright (c) 2003-2006 University of Chicago and Fellowship
# for Interpretations of Genomes. All Rights Reserved.
#
# This file is part of the SEED Toolkit.
#
# The SEED Toolkit is free software. You can redistribute
# it and/or modify it under the terms of the SEED Toolkit
# Public License.
#
# You should have received a copy of the SEED Toolkit Public License
# along with this program; if not write to the University of Chicago
# at info@ci.uchicago.edu or the Fellowship for Interpretation of
# Genomes at veronika@thefig.info or download a copy from
# http://www.theseed.org/LICENSE.TXT.
#


use strict;
use lib::Web_Config;
use ERDBtk;
use ERDBtk::PDocPage;
use ERDBtkExtras;

=head1 Database Definition Display Script

This script displays a database definition. The definition must be stored in the
C<DBD> subdirectory of the ERDB module as an XML file. It is designed for
displaying experimental databases that will eventually be exported to other environments.
The following CGI parameters are used.

=over 4

=item name

The base name of the DBD file, without the C<xml> extension.

=back

=cut

# Get the CGI query object.
my $cgi = CGI->new();
# Start the output page.
print CGI::header();
print CGI::start_html(-title => 'Database Design',
                      -style =>  { src => "css/ERDB.css" },
                      -script => { src => "lib/ERDB.js" });
# Insure we recover from errors.
eval {
    # Get the DBD name.
    my $dbdName = $cgi->param('name');
    if (! $dbdName) {
        print CGI::blockquote({ class => 'err'}, "No DBD name specified.") . "\n";
    } else {
        my $xmlFileName = "$FIG_Config::mod_base/ERDB/DBD/$dbdName.xml";
        if (! -f $xmlFileName) {
            print CGI::blockquote({ class => 'err'}, "Database definition file $dbdName not found.") . "\n";
        } else {
            # Remove the drive letter. It causes a 2048 error.
            $xmlFileName =~ s/^\w+://;
            # Get the database object. We don't pass a database handle because we are not connecting to the
            # database.
            my $erdb = ERDBtk->new(undef, $xmlFileName);
            # We're displaying a diagram. Get a page creator.
            my $page = ERDBtk::PDocPage->new(dbObject => $erdb);
            # Create the body HTML.
            my $html = CGI::div({ class => 'doc' }, $page->DocPage(boxHeight => 740));
            # Output it.
            print "$html\n";
        }
    }

};

if ($@) {
    # Here we have a fatal error. Save the message.
    my $errorText = "SCRIPT ERROR: $@";
    # Output the error message.
    print CGI::blockquote({ class => 'err' }, $errorText) . "\n";
}
# Close the page.
print CGI::end_html() . "\n";
