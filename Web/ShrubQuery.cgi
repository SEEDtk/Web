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
use Shrub;
use ERDB::PDocPage;
use ERDBExtras;
use ERDB::QueryConsole;
use Time::HiRes;

=head1 Shrub Query and Display Script

This script displays or queries the Shrub database. It uses L<ERDB::PDocPage>
to display the diagram or L<ERDB::QueryConsole> to display the results of a
query. If the action is C<Diagram>, all the other parameters are ignored.
The two scripts are combined to simplify the design of the input form.

The following CGI parameters are used.

=over 4

=item action

C<QUERY> to execute a query, C<Diagram> to display the database diagram.

=item path

The path through the database, as described in L<ERDB/Object Name List>.

=item filter

The filter clause for the query, as described in L<ERDB/Filter Clause>.

=item parms

The parameter values for the query, one per line of text. If code is being
generated, each parameter value can be preceded by a variable name (or L<get_all.pl>
column identifier) and an equal sign. The equal sign is presumed to be followed by
a single space, after which anything present serves as the value.

=item fields

A list of field names in L<standard field name format|ERDB/Standard Field Name Format>.

=item limit

The maximum number of result rows to display, or C<0> to display them all.

=item style

The style of code to generate for the code display at the end. The values are
C<Get> for a get-loop, C<GetAll> for a single L<GetAll|ERDB/GetAll> call, or
C<get_all> for a command-line invocation of the L<get_all.pl> command.

=back

=cut

# This hash is used to alternate the row styles.
use constant ODDEVEN => { 'odd' => 'even', 'even' => 'odd' };

# Get the CGI query object.
my $cgi = CGI->new();
# Start the output page.
print CGI::header();
print CGI::start_html(-title => 'Shrub Database',
                      -style =>  { src => "css/ERDB.css" },
                      -script => { src => "lib/ERDB.js" });
# Insure we recover from errors.
eval {
    # Is this a diagram or a query?
    my $action = $cgi->param('action');
    my $offline = ($action eq 'Diagram' ? 1 : 0);
    # Get the DBD name.
    my $xmlFileName = $FIG_Config::shrub_dbd;
    # Remove the drive letter. It causes a 2048 error.
    $xmlFileName =~ s/^\w+://;
    # Get the datanase object. Note that we don't connect to the database
    # if we're doing a diagram.
    my $shrub = Shrub->new(DBD => $xmlFileName, offline => $offline);
    if ($offline) {
        # We're displaying a diagram. Get a page creator.
        my $page = ERDB::PDocPage->new(dbObject => $shrub);
        # Create the body HTML.
        my $html = CGI::div({ class => 'doc' }, $page->DocPage(boxHeight => 740));
        # Output it.
        print "$html\n";
    } else {
        # Here we have a query. We'll accumulate HTML lines in here.
        my @lines = CGI::start_div({ class => 'doc' });
        # Create the query console helper.
        my $console = ERDB::QueryConsole->new($shrub, secure => 1);
        # Get the query parameters.
        my $path = $cgi->param('path');
        my $filter = $cgi->param('filter') // '';
        my $fields = $cgi->param('fields');
        my $style = $cgi->param('style') || '0';
        my $limit = $cgi->param('limit') || 100;
        # The parameters require special processing. We break them up into lines. In each line, we
        # need to check for a variable specification.
        my $parmText = $cgi->param('parms') // '';
        my (@parms, @vars);
        for my $parm (split /[\r\n]+/, $parmText) {
            # Do we have a variable spec?
            if ($parm =~ /^(\$\w+)\s+=\s(.+)/) {
                # Yes. Save it.
                push @parms, $2;
                $vars[$#parms] = $1;
            } else {
                # No, just save the value.
                push @parms, $parm;
            }
        }
        # Submit the query.
        my $start = time();
        my $okFlag = $console->Submit($path, $filter, \@parms, $fields, $limit);
        if (! $okFlag) {
            # The query failed. Produce an error message.
            push @lines, CGI::h3("Query Failed") . "\n";
            push @lines, $console->Summary();
        } else {
            # Here the query worked. We can display the output. Start with the code
            # (if any).
            if ($style eq 'Get' || $style eq 'GetAll') {
                # Yes. Generate the PERL code.
                my $code = $console->GetCode('shrub', $style, @vars);
                push @lines, CGI::h3("Perl Code for Query");
                push @lines, CGI::pre($code);
            } elsif ($style eq 'get_all') {
                # He wants a command line. Generate it.
                my $code = $console->GetCommand(@vars);
                my $mode = ($FIG_Config::win_mode ? "Windows" : "Unix");
                push @lines, CGI::h3("get_all Command for Query ($mode)");
                push @lines, CGI::pre($code);
            }
            # Now the results.
            push @lines, CGI::h3("Results");
            push @lines, CGI::start_table({ class => 'fancy' });
            # Get the headers.
            my (@aligns, @captions);
            for my $headerData ($console->Headers()) {
                push @aligns, $headerData->[1];
                push @captions, CGI::th({ class => $headerData->[1] }, $headerData->[0]);
            }
            # Remember the number of columns.
            my $n = scalar @captions;
            # Start with odd rows.
            my $rowClass = "odd";
            # Output the header row.
            push @lines, CGI::Tr(@captions);
            # Loop through the results, generating table rows.
            while (my $row = $console->GetRow()) {
                # We'll put the table cells in here.
                my @cells;
                # Loop through the results.
                for (my $i = 0; $i < $n; $i++) {
                    my $item = $row->[$i] || '';
                    push @cells, CGI::td({ class => $aligns[$i] }, $item);
                }
                # Output the row.
                push @lines, CGI::Tr({ class => $rowClass }, @cells);
                # Flip the row style.
                $rowClass = ODDEVEN->{$rowClass};
            }
            # Close the table.
            push @lines, CGI::end_table();
            # Record the time spent.
            $console->AddStat(duration => int(time() - $start));
            # Write the summary.
            push @lines, $console->Summary();
        }
        # Display the accumulated HTML.
        push @lines, CGI::end_div();
        print join("\n", @lines, "");
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
