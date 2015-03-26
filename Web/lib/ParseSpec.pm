#
# Copyright (c) 2003-2015 University of Chicago and Fellowship
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


package ParseSpec;

    use strict;
    use warnings;
    use File::Slurp;
    use Data::Dumper;
    use CGI;

=head1 Parse a kBase Spec File for Types

This module contains methods for parsing a kBase type specification and producing HTML output.

=head2 Public Methods

=head3 ToHtml

    my @lines = ParseSpec::ToHtml($specFile, $cgi);

Parse a kBase specification file and output the type definitions as Html. Each type definition will
be given a section in the table of contents, and references to other types in the file will be
linked. Comment sections will be associated with the subsequent type definition.

This method will make two passes over the data. The first pass will break the document into
sections based on the defined type. The second pass will turn each defined type into HTML.

=over 4

=item specFile

Name of the file containing the specification.

=item cgi

L<CGI> object for producing HTML output.

=item RETURN

Returns a list of HTML lines.

=back

=cut

sub ToHtml {
    # Get the parameters.
    my ($specFile) = @_;
    # This will be our return list.
    my @retVal;
    # We will stash the sections in here.
    my %typeHash;
    # Slurp in the spec file.
    my $spec = File::Slurp::read_file($specFile);
    # Extract the module name.
    my ($modComment, $modName, $modText) =
            $spec =~ /(?:\/\*\s*(.+?)\s*\*\/)?\s*module\s+(\S+)\s+{(.+)};/s;
    if (! $modName) {
        $modName = "Anonymous";
        $modText = $specFile;
    }
    # Now loop through the text, extracting sections.
    while ($modText =~ /typedef\s+(structure\s+{.+?}|tuple<.+?>|list<\S+>|\S+)\s+(\S+);/gs) {
        # Here we have a type definition. $1 is the definition itself, and $2 is the name.
        my ($def, $name) = ($1, $2);
        # Check for a comment.
        my $comment = FindComment($modText, $-[0]);
        $typeHash{$name} = [$comment, $def];
    }
    # It is now time to create the HTML lines. Start with a heading.
    push @retVal, CGI::div({ class => 'heading' }, CGI::h1($modName));
    push @retVal, CGI::start_div({ id => 'Pod' });
    # Put in the top-of-page anchor.
    push @retVal, CGI::a({ class => 'dummyTopAnchor', name => '___top' });
    # Next comes the table of contents.
    push @retVal, CGI::div({ class => 'indexgroup' }, CGI::ul({ class => 'indexlist indexlist1' },
            CGI::li({ class => 'indexItem indexItem1' }, [ map { CGI::a({ href => "#$_"}, $_) } sort keys %typeHash ])));
    # Now we loop through the types. The tricky part here is that we need to look inside the type text for
    # callbacks to other types.
    for my $type (sort keys %typeHash) {
        my ($comment, $def) = @{$typeHash{$type}};
        # Generate the section heading.
        push @retVal, CGI::h1(CGI::a({ class => 'u', href => '#___top', name => $type }, $type));
        # Add the comment (if any).
        if ($comment) {
            push @retVal, CGI::p($comment);
        }
        # Process according to the definition type.
        if ($def =~ /^structure\s*{(.+)}/s) {
            # Here we have a structure. The fields are displayed in a table.
            push @retVal, CGI::p('This type is a structure.');
            push @retVal, StructureBody($1, \%typeHash, ';');
        } elsif ($def =~ /^list<(\S+)>/s) {
            push @retVal, CGI::p('List of ' . ShowType($1, \%typeHash));
        } elsif ($def =~ /^tuple\s*<(.+)>/s) {
            # Here we have a tuple. This is defined like a structure, but with
            # commas instead of semicolons.
            push @retVal, CGI::p('This type is a tuple.');
            push @retVal, StructureBody($1, \%typeHash, ',');
        } else {
            push @retVal, CGI::p('Type of ' . ShowType($def, \%typeHash));
        }
    }
    # Close the section.
    push @retVal, CGI::end_div(), CGI::br({ class => 'clear' });
    # Return the HTML lines.
    return @retVal;
}


=head3 StructureBody

    my @lines = ParseSpec::StructureBody($def, \%typeHash, $delim);

Generate the HTML for the body of a complex type definition. This is always
in the form of multiple statements (terminated by a delimiter)
consisting of a type alone or a type followed by a field name. The complication is that
on occasion there will be a comment preceding the type.

=over 4

=item def

Text of the structure definition.

=item typeHash

Reference to a hash mapping each other type to its definition. This is used to determine
if we can link a type name to its section in the HTML document.

=item delim

Delimiter between statements.

=item RETURN

Returns a list of HTML lines to be used to document the type.

=back

=cut

sub StructureBody {
    # Get the parameters.
    my ($def, $typeHash, $delim) = @_;
    # Declare the return variable.
    my @retVal = CGI::start_table();
    # Split the text into statements.
    my @stmts = ComputeStatements($def, $delim);
    # Loop through the statements.
    for my $stmt (@stmts) {
        # Get the comment and text.
        my ($comment, $text) = @$stmt;
        # This will eventually contain the type and name.
        my ($type, $name);
        # Check for an explicit name.
        if ($text =~ /(\S.*\S)\s+(\w+)/) {
            ($type, $name) = ($1, $2);
        } elsif ($text =~ /(\S.*\S)/) {
            ($type, $name) = ($1, '');
        }
        # If we found something, form the table row.
        if ($type) {
            push @retVal, CGI::Tr(CGI::td([ShowType($type, $typeHash), $name, $comment]));
        }
    }
    # Close the table.
    push @retVal, CGI::end_table();
    # Return the result.
    return @retVal;
}


=head3 ShowType

    my $html = ShowType($type, $typeHash);

Display a type name in HTML. If the name is found in the type hash, we
wrap it in a link.

=over 4

=item type

Type name to display.

=item typeHash

Reference to a hash mapping each other type to its definition. This is used to determine
if we can link a type name to its section in the HTML document.

=item RETURN

Returns the type name in HTML.

=back

=cut

sub ShowType {
    # Get the parameters.
    my ($type, $typeHash) = @_;
    # Declare the return variable.
    my $retVal = $type;
    # Analyze the type.
    if ($type =~ /list\s*<(.+)>/) {
        # Here we have a list of another type.
        $retVal = "list of " . ShowType($1, $typeHash);
    } elsif ($type =~ /tuple\s*<(.+)>/) {
        # Here we have a tuple of other types.
        my @parts = split /\s*,\s*/, $1;
        $retVal = 'tuple of (' .  join(", ", map { ShowType($_, $typeHash) } @parts) . ')';
    } elsif (exists $typeHash->{$type}) {
        # Here we have a linkable type.
        $retVal = CGI::a({ href => "#$type" }, $retVal);
    }
    # Return the result.
    return $retVal;
}

=head3 ComputeStatements

    my @stmts = ParseSpec::ComputeStatements($text, $delim);

Split the specified text into statements based on the delimiter. We make the simplifying assumption that
comments occur at the beginning of statements, which is generally the case in typespecs.

=over 4

=item text

Text to split into statements.

=item delim

Delimiter between statements.

=item RETURN

Returns a list of 2-tuples, each consisting of a comment and a statement.

=back

=cut

sub ComputeStatements {
    # Get the parameters.
    my ($text, $delim) = @_;
    # First split out the comments.
    my @csplits = split /(\/\*.+?\*\/)/s, $text;
    # This will be the return area.
    my @retVal;
    # This will contain the current comment.
    my $comment = '';
    # Loop through the statements.
    for my $csplit (@csplits) {
        # Is this a comment?
        if ($csplit =~ /\/\*\s*(.+?)\s*\*\//s) {
            # Yes. Save it.
            $comment = FormatComment($1);
        } else {
            # No. Split it into statements. Note the comment only applies
            # to the first one.
            my @stmts = split $delim, $csplit;
            for my $stmt (@stmts) {
                push @retVal, [$comment, $stmt];
                $comment = '';
            }
        }
    }
    # Return the statement list.
    return @retVal;
}

=head3 FindComment

    my $comment = ParseSpec::FindComment($modText, $pos);

Check for a comment before the specified position in the specified
string. If no comment is found, return an empty string. The comment must
have nothing following it except whitespace.

=over 4

=item modText

String to scan for a comment.

=item pos

Position in the string the comment must precede.

=item RETURN

Returns the text of the comment, or an empty string if no comment was found.

=back

=cut

sub FindComment {
    # Get the parameters.
    my ($modText, $pos) = @_;
    # Declare the return variable.
    my $retVal;
    # Check for the existence of a comment. If we find one we store it in the
    # return variable. If we prove there isn't one we set the return variable
    # to an empty string.
    my $end = $pos - 1;
    while ($end > 0 && ! defined $retVal) {
        my $c = substr($modText, $end, 1);
        if ($c =~ /\s/) {
            # White space. Keep searching.
            $end--;
        } elsif ($c eq '/') {
            # Possible end of comment. Check the previous character.
            if (substr($modText, $end-1, 1) eq '*') {
                # We have a comment ending here. Find the rest.
                my $begin = rindex($modText, '/*', $end);
                if ($begin >= 0) {
                    $retVal = FormatComment(substr($modText, $begin+2, $end - $begin - 3));
                } else {
                    $retVal = '';
                }
            } else {
                $retVal = '';
            }
        } else {
            $retVal = '';
        }
    }
    # Return the result.
    return $retVal;
}


=head3 FormatComment

    my $html = FormatComment($text);

Format a comment for HTML. This involves looking for special indicators
that the text is not simply raw word sequences.

=over 4

=item text

Comment text to convert.

=item RETURN

A version of the comment text suitable for the interior of an HTML paragrapph.

=back

=cut

sub FormatComment {
    # Get the parameters.
    my ($text) = @_;
    # Declare the return variable.
    my $retVal = $text;
    # Remove excess spaces.
    $retVal =~ s/^\*\s+//;
    $retVal =~ s/\n\s+\*/ /gs;
    # Return the result.
    return CGI::i($retVal);
}



1;
