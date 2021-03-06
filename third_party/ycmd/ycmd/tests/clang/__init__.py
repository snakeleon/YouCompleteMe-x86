# Copyright (C) 2016 ycmd contributors
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import functools
import os
import tempfile
import contextlib
import json
import shutil

from ycmd import handlers
from ycmd.utils import ToUnicode
from ycmd.tests.test_utils import ClearCompletionsCache, SetUpApp

shared_app = None


def PathToTestFile( *args ):
  dir_of_current_script = os.path.dirname( os.path.abspath( __file__ ) )
  return os.path.join( dir_of_current_script, 'testdata', *args )


def setUpPackage():
  """Initializes the ycmd server as a WebTest application that will be shared
  by all tests using the SharedYcmd decorator in this package. Additional
  configuration that is common to these tests, like starting a semantic
  subserver, should be done here."""
  global shared_app

  shared_app = SetUpApp()


def SharedYcmd( test ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes the shared ycmd application as a parameter.

  Do NOT attach it to test generators but directly to the yielded tests."""
  global shared_app

  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    ClearCompletionsCache()
    return test( shared_app, *args, **kwargs )
  return Wrapper


def IsolatedYcmd( test ):
  """Defines a decorator to be attached to tests of this package. This decorator
  passes a unique ycmd application as a parameter. It should be used on tests
  that change the server state in a irreversible way (ex: a semantic subserver
  is stopped or restarted) or expect a clean state (ex: no semantic subserver
  started, no .ycm_extra_conf.py loaded, etc).

  Do NOT attach it to test generators but directly to the yielded tests."""
  @functools.wraps( test )
  def Wrapper( *args, **kwargs ):
    old_server_state = handlers._server_state

    try:
      test( SetUpApp(), *args, **kwargs )
    finally:
      handlers._server_state = old_server_state
  return Wrapper



@contextlib.contextmanager
def TemporaryClangTestDir():
  """Context manager to execute a test with a temporary workspace area. The
  workspace is deleted upon completion of the test. This is useful particularly
  for testing compilation databases, as they require actual absolute paths.
  See also |TemporaryClangProject|. The context manager yields the path of the
  temporary directory."""
  tmp_dir = tempfile.mkdtemp()
  try:
    yield tmp_dir
  finally:
    shutil.rmtree( tmp_dir )


@contextlib.contextmanager
def TemporaryClangProject( tmp_dir, compile_commands ):
  """Context manager to create a compilation database in a directory and delete
  it when the test completes. |tmp_dir| is the directory in which to create the
  database file (typically used in conjunction with |TemporaryClangTestDir|) and
  |compile_commands| is a python object representing the compilation database.

  e.g.:
    with TemporaryClangTestDir() as tmp_dir:
      database = [
        {
          'directory': os.path.join( tmp_dir, dir ),
          'command': compiler_invocation,
          'file': os.path.join( tmp_dir, dir, filename )
        },
        ...
      ]
      with TemporaryClangProject( tmp_dir, database ):
        <test here>

  The context manager does not yield anything.
  """
  path = os.path.join( tmp_dir, 'compile_commands.json' )

  with open( path, 'w' ) as f:
    f.write( ToUnicode( json.dumps( compile_commands, indent=2 ) ) )

  try:
    yield
  finally:
    os.remove( path )
