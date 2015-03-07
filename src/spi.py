#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import sys
import os
import subprocess
import urllib2
import re

# Internationalization
import locale
import gettext
gettext.install("spi", "/usr/share/locale", unicode=1)

slaptget = '/usr/sbin/slapt-get'
slaptsrc = '/usr/bin/slapt-src'
slackbuilds_data = '/usr/src/slapt-src/slackbuilds_data'

# create a copy of the default environment
initial_env = dict()

class Colours:
	RED = '\033[01;31m'
	GREEN = '\033[01;32m'
	YELLOW = '\033[01;33m'
	RESET = '\033[00m'

	def disable(self):
		self.RED = ''
		self.GREEN = ''
		self.YELLOW = ''
		self.RESET = ''

colour = Colours()

def set_output_encoding(encoding='utf-8'):
	import sys
	import codecs
	'''When piping to the terminal, python knows the encoding needed, and
	   sets it automatically. But when piping to another program (for example,
	   | less), python can not check the output encoding. In that case, it 
	   is None. What I am doing here is to catch this situation for both 
	   stdout and stderr and force the encoding'''
	current = sys.stdout.encoding
	if current is None :
		sys.stdout = codecs.getwriter(encoding)(sys.stdout)
	current = sys.stderr.encoding
	if current is None :
		sys.stderr = codecs.getwriter(encoding)(sys.stderr)

set_output_encoding()

def main(argv):
	try:
		opts, args = getopt.getopt(argv, "nhuUis", ["no-colour",
			"help", "update", "upgrade" , "install", "search", "show",
			"simulate", "clean"])
		
		do_show = False
		do_install = False
		do_simulate = False
		for opt, arg in opts:
			if opt in ("-n", "--no-colour"):
				colour.disable()
			elif opt in ("-h", "--help"):
				usage()
				sys.exit(0)
			elif opt in ("-u", "--update"):
				retval = update()
				sys.exit(retval)
			elif opt in ("-U", "--upgrade"):
				retval = upgrade()
				sys.exit(retval)
			elif opt in ("--show",):
				do_show = True
			elif opt in ("-i", "--install"):
				do_install = True
			elif opt in ("-s", "--simulate"):
				do_simulate = True
			elif opt in ("--clean",):
				retval = clean()
				sys.exit(retval)
			elif opt in ("--search",):
				pass
		if not len(args) > 0:
			usage()
			sys.exit(0)
		if do_show:
			show(args)
		elif do_install:
			if do_simulate:
				simulate(args)
			else:
				install(args)
		else:
			search(args)

	except getopt.GetoptError:
		usage()
		sys.exit(1)

def check_for_root():
	if os.geteuid() != 0:
		print _('This action requires root privileges.')
		sys.exit(1)

def string_red(string):
	return colour.RED+string+colour.RESET

def string_green(string):
	return colour.GREEN+string+colour.RESET

def string_yellow(string):
	return colour.YELLOW+string+colour.RESET

# Returns a list with the names of installed packages (names only)
def pkg_installed():
	pkg_installed = []
	for i in os.listdir('/var/log/packages'):
		pkg_installed.append(i.rpartition('-')[0].rpartition('-')[0].rpartition('-')[0])
	return pkg_installed

# Returns a list of packages that match the search criteria (args)
# Each entry in the list has the following format:
# [pkgshortname, pkginst, pkgdesc]
def pkglist(args):
	cmd = [slaptget, '--search']
	for arg in args:
		cmd.append(arg)
	env = dict()
	for i in initial_env:
		env[i] = initial_env[i]
	env['LANG'] = 'C'
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, env=env)
	pkglist_output = p.communicate()[0]
	status = p.returncode
	pkglist_output = pkglist_output.splitlines()
	pkgs = []
	pkgnames = []
	for line in pkglist_output:
		pkgfullname = line.partition('[inst=')[0]
		pkgshortname = pkgfullname.rpartition('-')[0].rpartition('-')[0].rpartition('-')[0]
		if pkgshortname not in pkgnames:
			pkgnames.append(pkgshortname)
			if pkgshortname in pkg_installed():
				pkginst = True
			else:
				pkginst = False
			pkgdesc = line.partition(']: ')[2] 
			pkgs.append([pkgshortname, pkginst, pkgdesc])
	return pkgs

# Returns a list of SlackBuilds that match the search criteria (args)
def slackbuildlist(args):
	cmd = [slaptsrc, '--search']
	for arg in args:
		cmd.append(arg)
	env = dict()
	for i in initial_env:
		env[i] = initial_env[i]
	env['LANG'] = 'C'
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
			stderr=subprocess.PIPE, env=env)
	pkglist_output = p.communicate()[0]
	status = p.returncode
	pkglist_output = pkglist_output.splitlines()
	pkgs = []
	pkgnames = []
	for line in pkglist_output:
		pkgfullname = line.partition(' - ')[0]
		pkgshortname = pkgfullname.rpartition(':')[0]
		if pkgshortname not in pkgnames:
			pkgnames.append(pkgshortname)
			if pkgshortname in pkg_installed():
				pkginst = True
			else:
				pkginst = False
			pkgdesc = line.partition(' - ')[2] 
			pkgs.append([pkgshortname, pkginst, pkgdesc])
	return pkgs

def search(args):
	# strip "lib" prefixes and suffixes in names, so when searching for
	# "libfoo" or "foolib" results for "foo" are shown
	args = striplib(args)
	print _('Available packages:')
	pl = pkglist(args)
	if pl == []:
		print _('None')
	else:
		for i in pl:
			pkgname, pkginst, pkgdesc  = i[0], i[1], i[2]
			if pkginst is True:
				pkginst = string_green(_('Installed'))
			else:
				pkginst = string_red(_('Not installed'))
			print pkgname+' ['+pkginst+']:', pkgdesc
	print "\n"+_('Available SlackBuilds:')
	sl = slackbuildlist(args)
	if sl == []:
		print _('None')
	else:
		for i in sl:
			pkgname, pkginst, pkgdesc  = i[0], i[1], i[2]
			if pkginst is True:
				pkginst = string_green(_('Installed'))
			else:
				pkginst = string_red(_('Not installed'))
			print pkgname+' ['+pkginst+']:', pkgdesc

# Simulates the installation of packages. Provides a list of packages
# and SlackBuilds that will be installed.
def simulate(args, done=True, pqueue=[], squeue=[], installed=[]):
	pl = pkglist(args)
	sl = slackbuildlist(args) 
	p = []
	for i in pl:
		p.append(i[0])
	s = []
	for i in sl:
		s.append(i[0])
	both = p+s
	if installed == []:
		installed = pkg_installed()
	for arg in args:
		if arg not in both:
			print string_red(_('No such package or SlackBuild:'))+' '+arg
			sys.exit(1)
		if ((arg not in installed) and (arg not in pqueue) and (arg not in squeue)):
			if arg in p:
				pqueue.append(arg)
			elif arg in s:
				squeue.append(arg)
				simulate(slaptsrcdeps(arg), False, pqueue, squeue, installed)
	if done:
		pqueue = sorted(slaptgetdeps(pqueue))
		squeue = sorted(squeue)
		if pqueue != []:
			print _('The following packages will be installed:')+'\n  ',
			for i in pqueue:
				print i,
		if squeue != []:
			if pqueue != []:
				print "\n"
			print _('The following SlackBuilds will be installed:')+'\n  ',
			for i in squeue:
				print i,
		if ((pqueue == []) and (squeue == [])):
			print _('Nothing to install')
		else:
			print ""

# Installs the packages/SlackBuilds that are given in args
def install(args):
	check_for_root()
	pl = pkglist(args)
	sl = slackbuildlist(args)
	p = []
	for i in pl:
		p.append(i[0])
	s = []
	for i in sl:
		s.append(i[0])
	for arg in args:
		if arg not in pkg_installed():
			if arg in p:
				installpkg(arg)
			elif arg in s:
				installsb(arg)
			else:
				print string_red(_('No such package or SlackBuild:'))+' '+arg
				sys.exit(1)

# installs packages, including any dependencies
def installpkg(pkg):
	p = subprocess.Popen([slaptget, '--no-prompt', '--install',
		pkg])
	retval = p.wait()
	if retval != 0:
		sys.exit(retval)

# installs SlackBuilds. Does not include dependencies.
def installsb(slackbuild):
	deps = slaptsrcdeps(slackbuild)
	if deps != []:
		install(deps)
	p = subprocess.Popen([slaptsrc, '--no-dep', '--yes', '--install',
		slackbuild])
	retval = p.wait()
	if retval != 0:
		sys.exit(retval)

# Cleans up the slapt-get and slapt-src caches
def clean():
	check_for_root()
	p = subprocess.Popen([slaptget, '--clean'])
	retval = p.wait()
	if retval == 0:
		p = subprocess.Popen([slaptsrc, '--clean'])
		retval = p.wait()
	return retval

# Updates the slapt-get and slapt-src repos
def update():
	check_for_root()
	print _('Updating package cache...')
	p = subprocess.Popen([slaptget, '--update'])
	retval = p.wait()
	if retval == 0:
		print "\n"+_('Updating SlackBuild cache...')
		p = subprocess.Popen([slaptsrc, '--update'])
		retval = p.wait()
	return retval

# Upgrades the packages with slapt-get
# No such thing is available for slapt-src
def upgrade():
	check_for_root()
	p = subprocess.Popen([slaptget, '--upgrade'])
	retval = p.wait()
	return retval

# Just a helper function used in show(args) below. It prints the header
# and footer, before displaying package/SlackBuild details respectively
def print_header(text, notext=False):
	line=""
	if notext:
		for i in range(0,73):
			line=line+"-"
		print string_yellow("+----")+string_yellow(line+"+")
	else:
		for i in range(0,71-len(text)):
			line=line+"-"
		print string_yellow("+----")+" "+text+" "+string_yellow(line+"+")

# a helper function that strips "lib" from the start and end of strings
# in lists. Replaces the "lib" part only if the string has some other
# chars in it.
def striplib(l):
	new = []
	for i in l:
		n = re.sub('^lib-(.)', r'\1', i)
		n = re.sub('(.)-lib$', r'\1', n)
		n = re.sub('^lib(.)', r'\1', n)
		n = re.sub('(.)lib$', r'\1', n)
		new.append(n)
	return new

# Shows information about package/SlackBuild. Essentially runs
# slapt-get --show or slapt-src --show
def show(args):
	args = set(args)
	l = len(args)
	pl = pkglist(args)
	sl = slackbuildlist(args)
	p = []
	for i in pl:
		p.append(i[0])
	s = []
	for i in sl:
		s.append(i[0])
	for arg in args:
		if arg in p:
			if (l>1):
				print_header(arg)
				sys.stdout.flush()
			process = subprocess.Popen([slaptget, '--show', arg])
			process.wait()
			if (l>1):
				print_header(arg, notext=True)
		elif arg in s:
			if (l>1):
				print_header(arg)
				sys.stdout.flush()
			process = subprocess.Popen([slaptsrc, '--show', arg])
			process.wait()
			if arg in pkg_installed():
				print _("Installed")+"."
			else:
				print _("Not installed")+"."
			
			# Now show the README if it's there
			#
			# just to be on the safe side
			sourceurl = None
			location = None
			files = None
			
			data = ''
			f = open(slackbuilds_data)
			done = False
			found = False
			while not done:
				line = f.readline()
				if line == 'SLACKBUILD NAME: '+arg+'\n':
					found = True
				if found is True:
					if line.startswith('SLACKBUILD'):
						data = ''.join([data, line])
					else:
						done = True
			f.close()
			pkginfo = data.splitlines()
			for i in pkginfo:
				if 'SLACKBUILD SOURCEURL: ' in i:
					sourceurl = i.partition('SOURCEURL: ')[2]
				elif 'SLACKBUILD LOCATION: ' in i:
					location = i.partition('LOCATION: ')[2]
				elif 'SLACKBUILD FILES: ' in i:
					files = i.partition('FILES: ')[2].rsplit(' ')
			if 'README' in files:
				try:
					# setting a timeout of 5 seconds. We don't want this to
					# take too long
					f = urllib2.urlopen(sourceurl+location+'README', None, 5)
					readme = f.read().splitlines()
					print "\nREADME:"
					for line in readme:
						try:
							print line.decode('utf8')
						except UnicodeDecodeError:
							print line.decode('latin1')
				except (urllib2.HTTPError, urllib2.URLError):
					pass
			# done, print the footer
			if (l>1):
				print_header(arg, notext=True)
		else:
			print string_red(_('No such package or SlackBuild:'))+' '+arg
		print
		sys.stdout.flush()


# Returns the dependencies of the packages included in pkgs.
# pkgs is a list of package names.
def slaptgetdeps(pkgs):
	deps = []
	DEVNULL = open('/dev/null', 'w')
	args = [slaptget, '--simulate', '--install']
	for i in pkgs:
		args.append(i)
	env = dict()
	for i in initial_env:
		env[i] = initial_env[i]
	env['LANG'] = 'C'
	p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=DEVNULL, env=env)
	output = p.communicate()[0]
	data = ''
	for line in output.splitlines():
		if line.endswith(' is to be installed'):
			data = line.rpartition(' is to be installed')[0].rpartition('-')[0].rpartition('-')[0].rpartition('-')[0]
			if data is not '':
				if data not in deps:
					deps.append(data)
	DEVNULL.close()
	return deps

# Returns the dependencies of a single SlackBuild (pkg)
def slaptsrcdeps(pkg):
	deps = []
	DEVNULL = open('/dev/null', 'w')
	args = [slaptsrc, '--show', pkg]
	env = dict()
	for i in initial_env:
		env[i] = initial_env[i]
	env['LANG'] = 'C'
	p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=DEVNULL, env=env)
	output = p.communicate()[0]
	data = ''
	for line in output.splitlines():
		if line.startswith('SlackBuild Requires:'):
			data = line.partition(':')[2]
	newdeps = data.replace('\n', ',').strip(' ').split(',')
	for i in newdeps:
		if i is not '' and i != '%README%':
			if i not in deps:
				deps.append(i)
	DEVNULL.close()
	return deps

def usage():
	print _('USAGE:'), 'spi',_('[OPTIONS] [STRING(s)]')
	print
	print _('OPTIONS:')
	print '       --search      ',_('search for specified packages (default action)')
	print '       --show        ',_('show details about package or SlackBuild')
	print '       --clean       ',_('purge package and SlackBuild caches')
	print '   -u, --update      ',_('update package and SlackBuild caches')
	print '   -U, --upgrade     ',_('upgrade packages')
	print '   -i, --install     ',_('install specified packages')
	print '   -s, --simulate    ',_('simulate installation of specified packages')
	print '   -n, --no-colour   ',_('disable colour output')
	print '   -h, --help        ',_('this help message')


if __name__ == "__main__":
	try:
		main(sys.argv[1:])
	except KeyboardInterrupt:
		sys.exit(2)
