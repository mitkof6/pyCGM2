# -*- coding: utf-8 -*-
"""
Created on Mon Oct 03 10:40:17 2016

@author: fabien Leboeuf ( Salford Univ)
"""

import pdb
import logging


import matplotlib.pyplot as plt

# pyCGM2 settings
import pyCGM2
pyCGM2.pyCGM2_CONFIG.setLoggingLevel(logging.INFO)

# vicon nexus
pyCGM2.pyCGM2_CONFIG.addNexusPythonSdk()
import ViconNexus


# openMA
pyCGM2.pyCGM2_CONFIG.addOpenma()
import ma.io
import ma.body
    
# pyCGM2 libraries    
import pyCGM2.smartFunctions as CGM2smart

    
if __name__ == "__main__":
    plt.close("all")    
    


#    pyNEXUS = ViconNexus.ViconNexus()    
#    NEXUS_PYTHON_CONNECTED = pyNEXUS.Client.IsConnected() 

    NEXUS_PYTHON_CONNECTED = True   
        
    if NEXUS_PYTHON_CONNECTED: 
        
        
        #---- INPUTS ----- 
        plotFlag = True #bool(int(sys.argv[1]))
        exportSpreadSheetFlag = True  #bool(int(sys.argv[2]))
        exportAnalysisC3dFlag = False
        normativeDataInput = "Schwartz2008_VeryFast"
        pointSuffix=""        
        
        normativeData = { "Author": normativeDataInput[:normativeDataInput.find("_")],"Modality": normativeDataInput[normativeDataInput.find("_")+1:]} 
        
        # ----DATA-----        
        DATA_PATH = "C:\\Users\\AAA34169\\Documents\\VICON DATA\\pyCGM2-Data\\CGM1\\CGM1-NexusPlugin\\CGM1-gaitProcessing\\"
        reconstructedFilenameLabelledNoExt ="gait Trial 01"  
        reconstructedFilenameLabelled = reconstructedFilenameLabelledNoExt+".c3d"        
    
        logging.info("data Path: "+ DATA_PATH)    
        logging.info( "reconstructed file: "+ reconstructedFilenameLabelled)
    
        # ----INFOS-----        
        model=None  
    
        subject=None
                         
        experimental=None
                     
        # ----PROCESSING-----
        CGM2smart.gaitProcessing_cgm1 (reconstructedFilenameLabelled, DATA_PATH,
                               model,  subject, experimental,
                               pointLabelSuffix = pointSuffix,
                               plotFlag= plotFlag, 
                               exportBasicSpreadSheetFlag = exportSpreadSheetFlag,
                               exportAdvancedSpreadSheetFlag = exportSpreadSheetFlag,
                               exportAnalysisC3dFlag = exportAnalysisC3dFlag,
                               consistencyOnly = True,
                               normativeDataDict = normativeData)
    else: 
        logging.error("Nexus Not Connected")