
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil
import rpm
import rpmfluff
import os.path
from data_setup import run_rpmdeplint


def test_catches_soname_change(request, dir_server):
    # This is the classic mistake repoclosure is supposed to find... the 
    # updated package has changed its soname, causing some other package's 
    # dependencies to become unresolvable.
    p_older = rpmfluff.SimpleRpmBuild('a', '4.0', '1', ['i386'])
    p_older.add_provides('libfoo.so.4')
    p_depending = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p_depending.add_requires('libfoo.so.4')
    baserepo = rpmfluff.YumRepoBuild([p_older, p_depending])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p_newer = rpmfluff.SimpleRpmBuild('a', '5.0', '1', ['i386'])
    p_newer.add_provides('libfoo.so.5')
    p_newer.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p_depending.get_base_dir())
        shutil.rmtree(p_older.get_base_dir())
        shutil.rmtree(p_newer.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p_newer.get_built_rpm('i386')])
    assert exitcode == 1
    assert err == ('Dependency problems with repos:\n'
            'nothing provides libfoo.so.4 needed by b-0.1-1.i386\n')


def test_catches_soname_change_with_package_rename(request, dir_server):
    # Slightly more complicated version of the above, where the old provider is 
    # not being updated but rather obsoleted.
    p_older = rpmfluff.SimpleRpmBuild('foolib', '4.0', '1', ['i386'])
    p_older.add_provides('libfoo.so.4')
    p_depending = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    p_depending.add_requires('libfoo.so.4')
    baserepo = rpmfluff.YumRepoBuild([p_older, p_depending])
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p_newer = rpmfluff.SimpleRpmBuild('libfoo', '5.0', '1', ['i386'])
    p_newer.add_obsoletes('foolib < 5.0-1')
    p_newer.add_provides('libfoo.so.5')
    p_newer.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p_depending.get_base_dir())
        shutil.rmtree(p_older.get_base_dir())
        shutil.rmtree(p_newer.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p_newer.get_built_rpm('i386')])
    assert exitcode == 1
    assert err == ('Dependency problems with repos:\n'
            'nothing provides libfoo.so.4 needed by b-0.1-1.i386\n')


def test_ignores_dependency_problems_in_packages_under_test(request, dir_server):
    # The check-sat command will find and report these problems, it would be 
    # redundant for check-repoclosure to also report the same problems.
    p2 = rpmfluff.SimpleRpmBuild('b', '0.1', '1', ['i386'])
    baserepo = rpmfluff.YumRepoBuild((p2,))
    baserepo.make('i386')
    dir_server.basepath = baserepo.repoDir

    p1 = rpmfluff.SimpleRpmBuild('a', '0.1', '1', ['i386'])
    p1.add_requires('doesnotexist')
    p1.make()

    def cleanUp():
        shutil.rmtree(baserepo.repoDir)
        shutil.rmtree(p2.get_base_dir())
        shutil.rmtree(p1.get_base_dir())
    request.addfinalizer(cleanUp)

    exitcode, out, err = run_rpmdeplint(['rpmdeplint', 'check-repoclosure',
                                         '--repo=base,{}'.format(dir_server.url),
                                         p1.get_built_rpm('i386')])
    assert exitcode == 0
    assert err == ''