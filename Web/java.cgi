#!/usr/bin/env perl

use strict;
use lib 'lib';
use CGI;
use Web_Config;
use IPC::Run3;

my $cgi = CGI->new();
print CGI::header();
print CGI::start_html(-title => "Java Test", -style =>  { src => "css/Basic.css" });
eval {
    my @cmd = split /\s/, "java -Dlogback.configurationFile=$FIG_Config::mod_base/kernel/jars/weblogback.xml -jar $FIG_Config::mod_base/kernel/jars/p3api.common.jar";
    push @cmd, "simple", "$FIG_Config::data/GTOcouple/83333.1.gto";
    my (@err, @out);
    my $rc = IPC::Run3::run3(\@cmd, \undef, \@out, \@err);
    print CGI::p("Return value is $rc.");
    print CGI::h1("Error output");
    print CGI::ul( map { CGI::li($_) } @err);
    print CGI::h1("Standard output");
    print CGI::ul( map { CGI::li($_) } @out);
};
if ($@) {
    print CGI::blockquote($@);
}
print CGI::end_html();

