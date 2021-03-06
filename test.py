#!/usr/bin/env python2

import locale

try: locale.setlocale( locale.LC_ALL, '' )
except: pass

from include import HydrusConstants as HC
from include import ClientConstants as CC
from include import HydrusGlobals as HG
from include import ClientDefaults
from include import ClientNetworking
from include import ClientServices
from include import HydrusPubSub
from include import HydrusSessions
from include import HydrusTags
from include import HydrusThreading
from include import TestClientConstants
from include import TestClientDaemons
from include import TestClientData
from include import TestClientListBoxes
from include import TestClientNetworking
from include import TestConstants
from include import TestDialogs
from include import TestDB
from include import TestFunctions
from include import TestClientImageHandling
from include import TestHydrusNATPunch
from include import TestHydrusNetworking
from include import TestHydrusSerialisable
from include import TestHydrusServer
from include import TestHydrusSessions
from include import TestHydrusTags
import collections
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import unittest
import wx
from twisted.internet import reactor
from include import ClientCaches
from include import ClientData
from include import HydrusData
from include import HydrusPaths

only_run = None

class Controller( object ):
    
    def __init__( self ):
        
        self.db_dir = tempfile.mkdtemp()
        
        TestConstants.DB_DIR = self.db_dir
        
        self._server_files_dir = os.path.join( self.db_dir, 'server_files' )
        self._updates_dir = os.path.join( self.db_dir, 'test_updates' )
        
        client_files_default = os.path.join( self.db_dir, 'client_files' )
        
        HydrusPaths.MakeSureDirectoryExists( self._server_files_dir )
        HydrusPaths.MakeSureDirectoryExists( self._updates_dir )
        HydrusPaths.MakeSureDirectoryExists( client_files_default )
        
        HG.controller = self
        HG.client_controller = self
        HG.server_controller = self
        HG.test_controller = self
        
        self.gui = self
        
        self._call_to_threads = []
        
        self._pubsub = HydrusPubSub.HydrusPubSub( self )
        
        self.new_options = ClientData.ClientOptions( self.db_dir )
        
        HC.options = ClientDefaults.GetClientDefaultOptions()
        
        self.options = HC.options
        
        def show_text( text ): pass
        
        HydrusData.ShowText = show_text
        
        self._reads = {}
        
        self._reads[ 'hydrus_sessions' ] = []
        self._reads[ 'local_booru_share_keys' ] = []
        self._reads[ 'messaging_sessions' ] = []
        self._reads[ 'tag_censorship' ] = []
        self._reads[ 'options' ] = ClientDefaults.GetClientDefaultOptions()
        self._reads[ 'file_system_predicates' ] = []
        self._reads[ 'media_results' ] = []
        
        self.example_tag_repo_service_key = HydrusData.GenerateKey()
        
        services = []
        
        services.append( ClientServices.GenerateService( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, CC.LOCAL_BOORU_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HC.COMBINED_LOCAL_FILE, CC.COMBINED_LOCAL_FILE_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_FILE_SERVICE_KEY, HC.LOCAL_FILE_DOMAIN, CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.TRASH_SERVICE_KEY, HC.LOCAL_FILE_TRASH_DOMAIN, CC.LOCAL_FILE_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( CC.LOCAL_TAG_SERVICE_KEY, HC.LOCAL_TAG, CC.LOCAL_TAG_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( self.example_tag_repo_service_key, HC.TAG_REPOSITORY, 'example tag repo' ) )
        services.append( ClientServices.GenerateService( CC.COMBINED_TAG_SERVICE_KEY, HC.COMBINED_TAG, CC.COMBINED_TAG_SERVICE_KEY ) )
        services.append( ClientServices.GenerateService( TestConstants.LOCAL_RATING_LIKE_SERVICE_KEY, HC.LOCAL_RATING_LIKE, 'example local rating like service' ) )
        services.append( ClientServices.GenerateService( TestConstants.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.LOCAL_RATING_NUMERICAL, 'example local rating numerical service' ) )
        
        self._reads[ 'services' ] = services
        
        client_files_locations = {}
        
        for prefix in HydrusData.IterateHexPrefixes():
            
            for c in ( 'f', 't', 'r' ):
                
                client_files_locations[ c + prefix ] = client_files_default
                
            
        
        self._reads[ 'client_files_locations' ] = client_files_locations
        
        self._reads[ 'sessions' ] = []
        self._reads[ 'tag_parents' ] = {}
        self._reads[ 'tag_siblings' ] = {}
        self._reads[ 'in_inbox' ] = False
        
        self._writes = collections.defaultdict( list )
        
        self._managers = {}
        
        self.services_manager = ClientCaches.ServicesManager( self )
        self.client_files_manager = ClientCaches.ClientFilesManager( self )
        
        self._managers[ 'tag_censorship' ] = ClientCaches.TagCensorshipManager( self )
        self._managers[ 'tag_siblings' ] = ClientCaches.TagSiblingsManager( self )
        self._managers[ 'tag_parents' ] = ClientCaches.TagParentsManager( self )
        self._managers[ 'undo' ] = ClientCaches.UndoManager( self )
        self.server_session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        self.local_booru_manager = ClientCaches.LocalBooruCache( self )
        
        self._cookies = {}
        
    
    def _GetCallToThread( self ):
        
        for call_to_thread in self._call_to_threads:
            
            if not call_to_thread.CurrentlyWorking():
                
                return call_to_thread
                
            
        
        if len( self._call_to_threads ) > 100:
            
            raise Exception( 'Too many call to threads!' )
            
        
        call_to_thread = HydrusThreading.THREADCallToThread( self )
        
        self._call_to_threads.append( call_to_thread )
        
        call_to_thread.start()
        
        return call_to_thread
        
    
    def _SetupWx( self ):
        
        self.locale = wx.Locale( wx.LANGUAGE_DEFAULT ) # Very important to init this here and keep it non garbage collected
        
        CC.GlobalBMPs.STATICInitialise()
        
        self.frame_icon = wx.Icon( os.path.join( HC.STATIC_DIR, 'hydrus_32_non-transparent.png' ), wx.BITMAP_TYPE_PNG )
        
    
    def pub( self, topic, *args, **kwargs ):
        
        pass
        
    
    def pubimmediate( self, topic, *args, **kwargs ):
        
        self._pubsub.pubimmediate( topic, *args, **kwargs )
        
    
    def sub( self, object, method_name, topic ):
        
        self._pubsub.sub( object, method_name, topic )
        
    
    def CallToThread( self, callable, *args, **kwargs ):
        
        call_to_thread = self._GetCallToThread()
        
        call_to_thread.put( callable, *args, **kwargs )
        
    
    CallToThreadLongRunning = CallToThread
    
    def DBCurrentlyDoingJob( self ):
        
        return False
        
    
    def GetFilesDir( self ):
        
        return self._server_files_dir
        
    
    def GetNewOptions( self ):
        
        return self.new_options
        
    
    def GetManager( self, manager_type ):
        
        return self._managers[ manager_type ]
        
    
    def GetWrite( self, name ):
        
        write = self._writes[ name ]
        
        del self._writes[ name ]
        
        return write
        
    
    def IsBooted( self ):
        
        return True
        
    
    def IsCurrentPage( self, page_key ):
        
        return False
        
    
    def IsFirstStart( self ):
        
        return True
        
    
    def IShouldRegularlyUpdate( self, window ):
        
        return True
        
    
    def ModelIsShutdown( self ):
        
        return HG.model_shutdown
        
    
    def PageCompletelyDestroyed( self, page_key ):
        
        return False
        
    
    def PageClosedButNotDestroyed( self, page_key ):
        
        return False
        
    
    def Read( self, name, *args, **kwargs ):
        
        return self._reads[ name ]
        
    
    def ReportDataUsed( self, num_bytes ):
        
        pass
        
    
    def ReportRequestUsed( self ):
        
        pass
        
    
    def ResetIdleTimer( self ): pass
    
    def Run( self ):
        
        self._SetupWx()
        
        suites = []
        
        if only_run is None: run_all = True
        else: run_all = False
        
        if run_all or only_run == 'daemons':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientDaemons ) )
            
        if run_all or only_run == 'data':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientConstants ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientData ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSerialisable ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusSessions ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
            
        if run_all or only_run == 'db':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
            
        if run_all or only_run == 'networking':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientNetworking ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusNetworking ) )
            
        if run_all or only_run == 'gui':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestDialogs ) )
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientListBoxes ) )
            
        if run_all or only_run == 'image':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestClientImageHandling ) )
            
        if run_all or only_run == 'nat':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusNATPunch ) )
            
        if run_all or only_run == 'server':
            
            suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusServer ) )
            
        
        suite = unittest.TestSuite( suites )
        
        runner = unittest.TextTestRunner( verbosity = 1 )
        
        runner.run( suite )
        
    
    def SetRead( self, name, value ):
        
        self._reads[ name ] = value
        
    
    def SetWebCookies( self, name, value ):
        
        self._cookies[ name ] = value
        
    
    def StartFileQuery( self, page_key, job_key, search_context ):
        
        pass
        
    
    def TidyUp( self ):
        
        time.sleep( 2 )
        
        HydrusPaths.DeletePath( self.db_dir )
        
    
    def ViewIsShutdown( self ):
        
        return HG.view_shutdown
        
    
    def WaitUntilModelFree( self ):
        
        return
        
    
    def WaitUntilViewFree( self ):
        
        return
        
    
    def Write( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
    
    def WriteSynchronous( self, name, *args, **kwargs ):
        
        self._writes[ name ].append( ( args, kwargs ) )
        
        if name == 'import_file':
            
            ( file_import_job, ) = args
            
            if file_import_job.GetHash().encode( 'hex' ) == 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08': # 'blarg' in sha256 hex
                
                raise Exception( 'File failed to import for some reason!' )
                
            else:
                
                return CC.STATUS_SUCCESSFUL
                
            
        
    
if __name__ == '__main__':
    
    args = sys.argv[1:]
    
    if len( args ) > 0:
        
        only_run = args[0]
        
    else: only_run = None
    
    try:
        
        threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        app = wx.App()
        
        controller = Controller()
        
        try:
            
            win = wx.Frame( None )
            
            def do_it():
                
                controller.Run()
                
                win.Destroy()
                
            
            wx.CallAfter( do_it )
            app.MainLoop()
            
        except:
            
            import traceback
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
        finally:
            
            HG.view_shutdown = True
            
            controller.pubimmediate( 'wake_daemons' )
            
            HG.model_shutdown = True
            
            controller.pubimmediate( 'wake_daemons' )
            
            controller.TidyUp()
            
        
    except:
        
        import traceback
        
        HydrusData.DebugPrint( traceback.format_exc() )
        
    finally:
        
        reactor.callFromThread( reactor.stop )
        
        print( 'This was version ' + str( HC.SOFTWARE_VERSION ) )
        
        raw_input()
        
