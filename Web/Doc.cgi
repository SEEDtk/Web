#!/usr/bin/env perl

use strict;
use CGI;
use Pod::Simple::HTML;
use lib 'lib';
use WebUtils;
use Web_Config;
use Env;
use ParseSpec;
use SeedTkRun;


=head1 Documentation Display

This script presents a form in which the user can enter a POD document or
PERL module name, The given document or module is then converted into HTML
and displayed. This provides a mechanism for access to the documentation
on the testing server.

The main CGI parameter is C<module>.

Several special module names give special results.

=over 4

=item FIG_Config

Display the project configuration parameters.

=item ENV

Display the system environment.

=item scripts

Display a list of the available command-line scripts.

=item p3

Display a list of the available PATRIC-3 scripts.

=back

=cut

# Get the CGI query object.
my $cgi = CGI->new();
# Get the module name parameter.
my $modName = $cgi->param('module');
# Compute the page title.
my $title = $modName || 'Documentation Page';
if ($modName eq 'p3') {
    $title = 'PATRIC-3 Scripts';
}
# Create the default output page header.
my @header = (CGI::header() .
        CGI::start_html(-title => $title,
                      -style => { src => 'css/Basic.css' }));
# Specify a borderless body.
push @header, CGI::start_body({ class => 'borderless' });
# Create the default output page trailer.
my @trailer = CGI::end_html();
# We'll put the HTML body text in here.
my @lines;
# Clear the trace file.
ClearTrace();
# Protect from errors.
eval {
    # Do we have a module?
    if ($modName eq 'FIG_Config') {
        # Here the user wants a dump of the FIG_Config. Get the data we need.
        my $configHash = Env::GetFigConfigs("$FIG_Config::proj/config/FIG_Config.pm");
        # Start with a heading.
        push @lines, CGI::div({ class => 'heading' }, CGI::h1("FIG_Config"));
        # Start the output table.
        push @lines, CGI::start_div({ id => 'Dump' }),
                CGI::start_table({ class => 'vars' }),
                CGI::Tr(CGI::th(['name', 'description', 'value']));
        # Loop through the variables, adding table rows.
        for my $var (sort keys %$configHash) {
            my $varData = $configHash->{$var};
            push @lines, CGI::Tr(CGI::td([$var, @$varData]));
        }
        # Close off the table.
        push @lines, CGI::end_table(), CGI::br({ class => 'clear' });
        # Close off the display area.
        push @lines, CGI::end_div();
    } elsif ($modName eq 'ENV') {
        # Here the user wants a dump of the environment variables.
        push @lines, CGI::div({ class => 'heading' }, CGI::h1("System Environment"));
        # Start the output table.
        push @lines, CGI::start_div({ id => 'Dump' }),
                CGI::start_table({ class => 'vars' }),
                CGI::Tr(CGI::th(['name', 'value']));
        # Loop through the environment variables, writing them out.
        for my $key (sort keys %ENV) {
            push @lines, CGI::Tr(CGI::td([$key, $ENV{$key}]));
        }
        # Close off the table.
        push @lines, CGI::end_table(), CGI::br({ class => 'clear' });
        # Close off the display area.
        push @lines, CGI::end_div();
    } elsif ($modName eq 'tutorials') {
        # Here the user wants a list of the tutorials.
        push @lines, CGI::div({ class => 'heading'}, CGI::h1("Tutorials"));
        push @lines, CGI::start_div({ id => 'Dump' });
        # Loop through the tutorial directory.
        my $tutDir = "$FIG_Config::web_dir/Tutorials";
        opendir (my $dh, $tutDir) || die "Could not open tutorial directory: $!";
        my @tuts = grep { $_ =~ /\.html$/i } readdir $dh;
        closedir $dh;
        # Sort the tutorial names.
        my @tutsInOrder = sort { Cmp($a, $b) } @tuts;
        # Start the list.
        push @lines, CGI::start_ol();
        for my $tut (@tutsInOrder) {
            # Compute the title.
            open(my $ih, "<$tutDir/$tut") || die "Could not open tutorial file $tut: $!";
            my $title;
            while (! eof $ih && ! $title) {
                my $line = <$ih>;
                if ($line =~ /<title>(.+)<\/title>/i) {
                    $title = $1;
                }
            }
            push @lines, CGI::li({ class => 'item' }, CGI::a({ href => "Tutorials/$tut" }, $tut) .
                                ": $title");
        }
        push @lines, CGI::end_ol();
        # Close off the display.
        push @lines, CGI::br({ class => 'clear' }), CGI::end_div();
    } elsif ($modName eq 'scripts') {
        # Here the user wants a list of the command-line scripts.
        push @lines, CGI::div({ class => 'heading'}, CGI::h1("Command-Line Scripts"));
        push @lines, CGI::start_div({ id => 'Dump' });
        # Loop through the script directories.
        for my $dir (@FIG_Config::scripts) {
            # Get the base name of the path and use it as our section title.
            $dir =~ /\/(\w+)\/scripts$/;
            push @lines, CGI::h2($1);
            # Get a hash of the scripts in this directory.
            my $scriptHash = Env::GetScripts($dir);
            if (! scalar keys %$scriptHash) {
                # Here there are none.
                push @lines, CGI::p("No documented scripts found.");
            } else {
                # We need to loop through the scripts, displaying them.
                # This variable will count undocumented scripts.
                my @undoc;
                # Sort the script names.
                my @scripts = sort { Cmp($a, $b) } keys %$scriptHash;
                # This variable will count documented scripts.
                my $doc = 0;
                # Do the looping.
                for my $script (@scripts) {
                    # Get the comment.
                    my $comment = $scriptHash->{$script};
                    # Are we documented?
                    if ($comment) {
                        # Yes. If this is the first one, start the list.
                        if (! $doc) {
                            push @lines, CGI::start_ol();
                        }
                        # Count this script and display it.
                        push @lines, CGI::li({ class => 'item' }, CGI::a({ href => "Doc.cgi?module=$script" }, $script) .
                                ": $comment");
                        $doc++;
                    } else {
                        # Undocumented script. Just remember it.
                        push @undoc, $script;
                    }
                }
                # If we had documented scripts, close the list.
                if ($doc) {
                    push @lines, CGI::end_ol();
                }
                # If we had undocumented scripts, list them.
                if (scalar @undoc) {
                    push @lines, CGI::p("Undocumented scripts: " . join(", ", @undoc));
                }
            }
        }
        # Close off the display.
        push @lines, CGI::end_ul(), CGI::br({ class => 'clear' }), CGI::end_div();
    } elsif ($modName eq 'p3') {
        # Here the user wants a list of the p3 command-line scripts.
        push @lines, CGI::div({ class => 'heading'}, CGI::h1("PATRIC-3 Scripts"));
        push @lines, CGI::start_div({ id => 'Dump' });
        my $dir = "$FIG_Config::mod_base/p3_scripts/scripts";
        # Get a hash of the scripts in this directory.
        my $scriptHash = Env::GetScripts($dir);
        if (! scalar keys %$scriptHash) {
            # Here there are none.
            push @lines, CGI::p("No documented scripts found.");
        } else {
            # We need to loop through the scripts, displaying them. This will be set to TRUE if we find
            # a documented script.
            my $doc;
            # Sort the script names and filter for p3s.
            my @scripts = sort { Cmp($a, $b) } keys %$scriptHash;
            # Do the looping.
            for my $script (@scripts) {
                # Get the comment.
                my $comment = $scriptHash->{$script};
                # Are we documented?
                if ($comment) {
                    # Yes. If this is the first one, start the list.
                    if (! $doc) {
                        push @lines, CGI::start_ol();
                    }
                    # Count this script and display it.
                    push @lines, CGI::li({ class => 'item' }, CGI::a({ href => "Doc.cgi?module=$script" }, $script) .
                            ": $comment");
                    $doc++;
                }
            }
            # If we had documented scripts, close the list.
            if ($doc) {
                push @lines, CGI::end_ol();
            }
        }
        # Close off the display.
        push @lines, CGI::end_ul(), CGI::br({ class => 'clear' }), CGI::end_div();
    } elsif ($modName =~ /^perl\s+(\S+)$/) {
        # Generate a redirection script for the specified perl function.
        push @lines, "<script>", "window.location='http://perldoc.perl.org/functions/$1.html';", "</script>";
    } elsif ($modName) {
        # Here we have a regular module. Try to find it.
        my $fileFound = FindPod($modName);
        if (! $fileFound) {
            push @lines, CGI::h3("Module $modName not found.");
        } elsif ($modName =~ /\.spec/) {
            # This is a type specification file.
            my $parser = ParseSpec->new();
            push @lines, $parser->ToHtml($fileFound);
            # Tell the user where the file came from.
            push @lines, CGI::p("Module $modName is located at $fileFound.\n");
        } else {
            # We have a file containing our module documentation in POD form.
            # Tell the user its name.
            push @lines, CGI::div({ class => 'heading'}, CGI::h1($modName));
            # Now we must convert the pod to HTML. To do that, we need a parser.
            my $parser = Pod::Simple::HTML->new();
            # Denote we want an index.
            $parser->index(1);
            # Make us the L-link URL.
            $parser->perldoc_url_prefix("Doc.cgi?module=");
            # Denote that we want to format the Pod into a string.
            my $pod;
            $parser->output_string(\$pod);
            # Parse the file.
            $parser->parse_file($fileFound);
            # Check for a meaningful result.
            if ($pod !~ /\S/) {
                # No luck. Output an error message.
                $pod = CGI::h3("No POD documentation found in <u>$modName</u>.");
            }
            # Put the result in the output area.
            push @lines, CGI::div({ id => 'Pod' }, $pod, CGI::br({ class => 'clear' }));
            # Tell the user where the file came from.
            my $name = ($modName =~ /\.pl$/ ? "Script " : "Module ") . $modName;
            push @lines, CGI::p("$name is located at $fileFound.\n");
            # Now we want to find the TODOs and USEs. For the USEs, we map them to the type
            # of USE. Currently, only "use base" is supported in this way. We also look for
            # a ScriptUtils::Opts call.
            my (@todoList, %useHash, $optCalled);
            if (! open(my $ih, "<$fileFound")) {
                # Here we could not open the file.
                push @lines, CGI::h3("Error opening file for TODO search: $!");
            } else {
                # Loop through the file, extracting TODOs and USEs.
                while (! eof $ih) {
                    my $line = <$ih>;
                    if ($line =~ /##\s*TODO\s+(.+)/) {
                        # Here we have a TODO.
                        push @todoList, $1;
                    } elsif ($line =~ /^\s*use\s+base\s+(?:qw\(|'|")([^)'"]+)/) {
                        # Here we have a use base.
                        if ($1 ne 'Exporter') {
                            $useHash{$1} = 'Base';
                        }
                    } elsif ($line =~ /^\s*use\s+(\w+);/) {
                        # Here we have a normal use.
                        $useHash{$1} = '';
                    } elsif ($line =~ /^[^#]+(?:ScriptUtils::Opts|P3Utils::script_opts|ServicesUtils::get_options|Job->new)\(/) {
                        # Here the user called ScriptUtils::Opts. We can generate a usage
                        # help dump.
                        $optCalled = 1;
                    }
                }
                # Write out the usage dump.
                if ($optCalled && $modName =~ /^(.+)\.pl$/) {
                    # Here we have a script that uses our standard options call. We can generate
                    # a usage statement.
                    my $cmd = $1;
                    push @lines, CGI::h1("USAGE");
                    my @usage;
                    eval {
                        @usage = SeedTkRun::run_gathering_output('perl', $fileFound, '--help'); ##`$cmd --help`;
                    };
                    if ($@) {
                        push @lines, CGI::blockquote("Script has error: $@");
                    } else {
                        # Here we successfully got the usage data.
                        push @lines, CGI::div({ class => 'pod' }, CGI::pre(join("\n", @usage)));
                    }
                }
                # Write out the use list.
                if (scalar(keys %useHash)) {
                    push @lines, CGI::h1("MODULES");
                    push @lines, CGI::start_ul();
                    for my $subModule (sort keys %useHash) {
                        my $line = CGI::a({ href => "Doc.cgi?module=$subModule"}, $subModule);
                        if ($useHash{$subModule}) {
                            $line .= " ($useHash{$subModule})";
                        }
                        push @lines, CGI::li($line);
                    }
                    push @lines, CGI::end_ul();
                }
                # Write out the TODO list.
                if (scalar(@todoList)) {
                    push @lines, CGI::h1("TO DO");
                    push @lines, CGI::start_ol();
                    push @lines, map { CGI::li($_) } @todoList;
                    push @lines, CGI::end_ol();
                    push @lines, CGI::br({ class => 'clear' });
                }
            }
        }
        push @lines, CGI::end_html();
    }
    print join("\n", @header, @lines, @trailer);
};
# Process any error.
if ($@) {
    print join("\n", @header,  CGI::blockquote($@), @trailer);
}

=head3 FindPod

    my $fileFound = FindPod($modName);

Attempt to find a POD document with the given name. If found, the file
name will be returned.

=over 4

=item modName

Name of the Pod module.

=item RETURN

Returns the name of the POD file found, or C<undef> if no such file was found.

=back

=cut

sub FindPod {
    # Get the parameters.
    my ($modName) = @_;
    # Declare the return variable.
    my $retVal;
    # Insure the name is reasonable.
    if ($modName =~ /^(?:\w|::|\-)+(?:\.(?:pl|spec|cgi))?$/) {
        # Convert the module name to a path.
        $modName =~ s/::/\//g;
        # Get a list of the possible file names for our desired file.
        my @files;
        if ($modName eq 'Config.pl') {
            @files = ("$FIG_Config::proj/Config.pl");
        } elsif ($modName =~ /\.pl/) {
            my @allScripts = ("$FIG_Config::userHome/dev_container/modules/app_service/scripts", @FIG_Config::scripts);
            @files = map { "$_/$modName" } @allScripts;
        } elsif ($modName =~ /\.spec/) {
            @files = map { "$_/$modName" } @FIG_Config::libs;
        } elsif ($modName =~ /\.cgi/) {
            @files = ("$FIG_Config::web_dir/$modName");
        } else {
             @files = map { ("$_/$modName.pod", "$_/$modName.pm", "$_/pods/$modName.pod") } @INC;
             push @files, map { ("$_/$modName.pod", "$_/$modName.pm") } @FIG_Config::libs;
        }
        # Find the first file that exists.
        for (my $i = 0; $i <= $#files && ! defined $retVal; $i++) {
            # Get the file name.
            my $fileName = $files[$i];
            # Fix windows/Unix file name confusion.
            $fileName =~ s#\\#/#g;
            if (-f $fileName) {
                $retVal = $fileName;
            }
        }
    }
    # Return the result.
    return $retVal;
}

