# -*- coding: utf-8 -*-
#import ipdb
import logging
import matplotlib.pyplot as plt
import argparse


# pyCGM2 settings
import pyCGM2

# pyCGM2 libraries
from pyCGM2.Tools import btkTools
from pyCGM2 import enums

from pyCGM2.Model import modelFilters, modelDecorator,bodySegmentParameters
from pyCGM2.Model.CGM2 import cgm
from pyCGM2.Model.CGM2 import decorators
from pyCGM2.ForcePlates import forceplates



def calibrate(DATA_PATH,calibrateFilenameLabelled,translators,
              required_mp,optional_mp,
              leftFlatFoot,rightFlatFoot,markerDiameter,
              pointSuffix,**kwargs):
    """
    Calibration of the CGM1

    :param DATA_PATH [str]: path to your data
    :param calibrateFilenameLabelled [str]: c3d file
    :param translators [dict]:  translators to apply
    :param required_mp [dict]: required anthropometric data
    :param optional_mp [dict]: optional anthropometric data (ex: LThighOffset,...)
    :param leftFlatFoot [bool]: enable of the flat foot option for the left foot
    :param rightFlatFoot [bool]: enable of the flat foot option for the right foot
    :param markerDiameter [double]: marker diameter (mm)
    :param pointSuffix [str]: suffix to add to model outputs

    """

    # --------------------------ACQUISITION ------------------------------------

    # ---btk acquisition---
    acqStatic = btkTools.smartReader(str(DATA_PATH+calibrateFilenameLabelled))
    btkTools.checkMultipleSubject(acqStatic)

    acqStatic =  btkTools.applyTranslators(acqStatic,translators)


    # ---check marker set used----
    dcm= cgm.CGM.detectCalibrationMethods(acqStatic)

    # ---definition---
    model=cgm.CGM1()
    model.configure(acq=acqStatic,detectedCalibrationMethods=dcm)
    model.addAnthropoInputParameters(required_mp,optional=optional_mp)

    # --store calibration parameters--
    model.setStaticFilename(calibrateFilenameLabelled)
    model.setCalibrationProperty("leftFlatFoot",leftFlatFoot)
    model.setCalibrationProperty("rightFlatFoot",rightFlatFoot)
    model.setCalibrationProperty("markerDiameter",markerDiameter)


    # --------------------------STATIC CALBRATION--------------------------
    scp=modelFilters.StaticCalibrationProcedure(model) # load calibration procedure

    # ---initial calibration filter----
    modelFilters.ModelCalibrationFilter(scp,acqStatic,model,
                                        leftFlatFoot = leftFlatFoot,
                                        rightFlatFoot = rightFlatFoot,
                                        markerDiameter = markerDiameter,
                                        viconCGM1compatible=True
                                        ).compute()
    # ---- Decorators -----
    decorators.applyBasicDecorators(dcm, model,acqStatic,optional_mp,markerDiameter,cgm1only=True)
    pigStaticMarkers = cgm.CGM.get_markerLabelForPiGStatic(dcm)

    # ----Final Calibration filter if model previously decorated -----
    if model.decoratedModel:
        # initial static filter
        modelFilters.ModelCalibrationFilter(scp,acqStatic,model,
                           leftFlatFoot = leftFlatFoot, rightFlatFoot = rightFlatFoot,
                           markerDiameter=markerDiameter,
                           viconCGM1compatible=True).compute()


    # ----------------------CGM MODELLING----------------------------------
    # ----motion filter----
    # notice : viconCGM1compatible option duplicate error on Construction of the foot coordinate system

    modMotion=modelFilters.ModelMotionFilter(scp,acqStatic,model,enums.motionMethod.Determinist,
                                              markerDiameter=markerDiameter,
                                              viconCGM1compatible=False,
                                              pigStatic=True,
                                              useLeftKJCmarker=pigStaticMarkers[0], useLeftAJCmarker=pigStaticMarkers[1],
                                              useRightKJCmarker=pigStaticMarkers[2], useRightAJCmarker=pigStaticMarkers[3])
    modMotion.compute()


    if "displayCoordinateSystem" in kwargs.keys() and kwargs["displayCoordinateSystem"]:
        csp = modelFilters.ModelCoordinateSystemProcedure(model)
        csdf = modelFilters.CoordinateSystemDisplayFilter(csp,model,acqStatic)
        csdf.setStatic(False)
        csdf.display()

    #---- Joint kinematics----
    # relative angles
    modelFilters.ModelJCSFilter(model,acqStatic).compute(description="vectoriel", pointLabelSuffix=pointSuffix)


    # detection of traveling axis + absolute angle
    if model.m_bodypart != enums.BodyPart.UpperLimb:
        longitudinalAxis,forwardProgression,globalFrame = btkTools.findProgressionAxisFromPelvicMarkers(acqStatic,["LASI","LPSI","RASI","RPSI"])
    else:
        longitudinalAxis,forwardProgression,globalFrame = btkTools.findProgressionAxisFromLongAxis(acqStatic,"C7","CLAV")

    if model.m_bodypart != enums.BodyPart.UpperLimb:
            modelFilters.ModelAbsoluteAnglesFilter(model,acqStatic,
                                                   segmentLabels=["Left Foot","Right Foot","Pelvis"],
                                                    angleLabels=["LFootProgress", "RFootProgress","Pelvis"],
                                                    eulerSequences=["TOR","TOR", "TOR"],
                                                    globalFrameOrientation = globalFrame,
                                                    forwardProgression = forwardProgression).compute(pointLabelSuffix=pointSuffix)

    if model.m_bodypart == enums.BodyPart.LowerLimbTrunk:
            modelFilters.ModelAbsoluteAnglesFilter(model,acqStatic,
                                          segmentLabels=["Thorax"],
                                          angleLabels=["Thorax"],
                                          eulerSequences=["YXZ"],
                                          globalFrameOrientation = globalFrame,
                                          forwardProgression = forwardProgression).compute(pointLabelSuffix=pointSuffix)

    if model.m_bodypart == enums.BodyPart.UpperLimb or model.m_bodypart == enums.BodyPart.FullBody:

            modelFilters.ModelAbsoluteAnglesFilter(model,acqStatic,
                                          segmentLabels=["Thorax","Head"],
                                          angleLabels=["Thorax", "Head"],
                                          eulerSequences=["YXZ","TOR"],
                                          globalFrameOrientation = globalFrame,
                                          forwardProgression = forwardProgression).compute(pointLabelSuffix=pointSuffix)
    # BSP model
    bspModel = bodySegmentParameters.Bsp(model)
    bspModel.compute()

    if  model.m_bodypart == enums.BodyPart.FullBody:
        modelFilters.CentreOfMassFilter(model,acqStatic).compute(pointLabelSuffix=pointSuffix)

    return model, acqStatic


def fitting(model,DATA_PATH, reconstructFilenameLabelled,
    translators,
    markerDiameter,
    pointSuffix,
    mfpa,
    momentProjection,**kwargs):

    """
    Fitting of the CGM1

    :param model [str]: pyCGM2 model previously calibrated
    :param DATA_PATH [str]: path to your data
    :param reconstructFilenameLabelled [string list]: c3d files
    :param translators [dict]:  translators to apply
    :param mfpa [str]: manual force plate assignement
    :param markerDiameter [double]: marker diameter (mm)
    :param pointSuffix [str]: suffix to add to model outputs
    :param momentProjection [str]: Coordinate system in which joint moment is expressed

    """

    # --------------------------ACQUISITION ------------------------------------

    # --- btk acquisition ----
    acqGait = btkTools.smartReader(str(DATA_PATH + reconstructFilenameLabelled))

    btkTools.checkMultipleSubject(acqGait)
    acqGait =  btkTools.applyTranslators(acqGait,translators)
    trackingMarkers = model.getTrackingMarkers()
    validFrames,vff,vlf = btkTools.findValidFrames(acqGait,trackingMarkers)

    scp=modelFilters.StaticCalibrationProcedure(model) # procedure

    # ---Motion filter----
    modMotion=modelFilters.ModelMotionFilter(scp,acqGait,model,enums.motionMethod.Determinist,
                                              markerDiameter=markerDiameter,
                                              viconCGM1compatible=True)

    modMotion.compute()

    if "displayCoordinateSystem" in kwargs.keys() and kwargs["displayCoordinateSystem"]:
        csp = modelFilters.ModelCoordinateSystemProcedure(model)
        csdf = modelFilters.CoordinateSystemDisplayFilter(csp,model,acqGait)
        csdf.setStatic(False)
        csdf.display()

    #---- Joint kinematics----
    # relative angles
    modelFilters.ModelJCSFilter(model,acqGait).compute(description="vectoriel", pointLabelSuffix=pointSuffix)

    # detection of traveling axis + absolute angle
    if model.m_bodypart != enums.BodyPart.UpperLimb:
        longitudinalAxis,forwardProgression,globalFrame = btkTools.findProgressionAxisFromPelvicMarkers(acqGait,["LASI","LPSI","RASI","RPSI"])
    else:
        longitudinalAxis,forwardProgression,globalFrame = btkTools.findProgressionAxisFromLongAxis(acqGait,"C7","CLAV")

    if model.m_bodypart != enums.BodyPart.UpperLimb:
            modelFilters.ModelAbsoluteAnglesFilter(model,acqGait,
                                                   segmentLabels=["Left Foot","Right Foot","Pelvis"],
                                                    angleLabels=["LFootProgress", "RFootProgress","Pelvis"],
                                                    eulerSequences=["TOR","TOR", "TOR"],
                                                    globalFrameOrientation = globalFrame,
                                                    forwardProgression = forwardProgression).compute(pointLabelSuffix=pointSuffix)

    if model.m_bodypart == enums.BodyPart.LowerLimbTrunk:
            modelFilters.ModelAbsoluteAnglesFilter(model,acqGait,
                                          segmentLabels=["Thorax"],
                                          angleLabels=["Thorax"],
                                          eulerSequences=["YXZ"],
                                          globalFrameOrientation = globalFrame,
                                          forwardProgression = forwardProgression).compute(pointLabelSuffix=pointSuffix)

    if model.m_bodypart == enums.BodyPart.UpperLimb or model.m_bodypart == enums.BodyPart.FullBody:

            modelFilters.ModelAbsoluteAnglesFilter(model,acqGait,
                                          segmentLabels=["Thorax","Head"],
                                          angleLabels=["Thorax", "Head"],
                                          eulerSequences=["YXZ","TOR"],
                                          globalFrameOrientation = globalFrame,
                                          forwardProgression = forwardProgression).compute(pointLabelSuffix=pointSuffix)


    #---- Body segment parameters----
    bspModel = bodySegmentParameters.Bsp(model)
    bspModel.compute()

    #---- CentreOfMass----
    if  model.m_bodypart == enums.BodyPart.FullBody:
        modelFilters.CentreOfMassFilter(model,acqGait).compute(pointLabelSuffix=pointSuffix)

    # Inverse dynamics
    if model.m_bodypart != enums.BodyPart.UpperLimb:
        # --- force plate handling----
        # find foot  in contact
        mappedForcePlate = forceplates.matchingFootSideOnForceplate(acqGait,mfpa=mfpa)
        forceplates.addForcePlateGeneralEvents(acqGait,mappedForcePlate)
        logging.warning("Manual Force plate assignment : %s" %mappedForcePlate)


        # assembly foot and force plate
        modelFilters.ForcePlateAssemblyFilter(model,acqGait,mappedForcePlate,
                                 leftSegmentLabel="Left Foot",
                                 rightSegmentLabel="Right Foot").compute()


        #---- Joint kinetics----
        idp = modelFilters.CGMLowerlimbInverseDynamicProcedure()
        modelFilters.InverseDynamicFilter(model,
                             acqGait,
                             procedure = idp,
                             projection = momentProjection,
                             viconCGM1compatible=True
                             ).compute(pointLabelSuffix=pointSuffix)


        #---- Joint energetics----
        modelFilters.JointPowerFilter(model,acqGait).compute(pointLabelSuffix=pointSuffix)

    #---- zero unvalid frames ---
    btkTools.applyValidFramesOnOutput(acqGait,validFrames)

    return acqGait
