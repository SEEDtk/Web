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
use Data::Dumper;

=head1 SEEDtk Server Script

This script processes a server request. It loads the appropriate module, then calls its execution
method and outputs the result as text.

The C<action> CGI parameter contains the name of the module to call. The other CGI parameters are
passed to the execution method as a hash reference. The name of the parameter will be the hash key,
the value will be a list of the parameter values.

The execution method has the following signature.

    my $output = Module::exec($shrub, \%parms);

The output should be a text string, possibly a json-encoded object.

=cut

## This constant contains the legal module names.
use constant MODULES => { Genome => 1, upload=>1 };

# Get the CGI query object.
my $cgi = CGI->new();

# Create the Shrub object.
my $shrub = Shrub->new();
# Get the module name.
my $modName = $cgi->param('action');
if (! $modName) {
    die "Missing action parameter. Choose one of (" . join(", ", keys %{MODULES()}) . ").";
} elsif (! MODULES->{$modName}) {
    die "Invalid action parameter $modName.";
}
# Compute the parameters.
my %parms = map { $_ => [$cgi->param($_)] } grep { $_ ne 'action' } $cgi->param;
# Load the module.
require "SVR/$modName.pm";
my $result = eval('SVR::' . $modName . '::exec($shrub, \%parms)');
if ($@) {
    die "Execution error: $@";
} else {
    print CGI::header('text/plain');
    print $result;
}
