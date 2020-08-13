#!/usr/bin/env perl

use strict;
use lib 'lib';
use CGI;
use Web_Config;
use IPC::Run3;

my $cgi = CGI->new();
my $debug = $cgi->param('debug');
print CGI::header();
print CGI::start_html(-title => "Java Test", -style =>  { src => "css/Basic.css" });
eval {
    my @cmd = split /\s/, "java -Dlogback.configurationFile=$FIG_Config::mod_base/kernel/jars/weblogback.xml -jar $FIG_Config::mod_base/kernel/jars/web.utils.jar";
    push @cmd, "A_new_toxin_-_antitoxin_system", "$FIG_Config::data/CoreSEED/FIG/Data";
    my (@err, @out);
    my $rc = IPC::Run3::run3(\@cmd, \undef, undef, \@err);
    if ($debug) {
        print CGI::h2("Log Messages");
        print CGI::p("Return code is $rc.");
        print CGI::ul(CGI::li(\@err));
    }
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();

