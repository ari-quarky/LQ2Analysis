#!/usr/bin/python
from datetime import datetime
import sys
sys.argv.append( '-b True' )
from ROOT import *
import ROOT
import array
import math
from argparse import ArgumentParser
tRand = TRandom3()
from random import randint

gSystem.Load('libCondFormatsBTauObjects')
gSystem.Load('libCondToolsBTau')
# get the sf data loaded
calib = BTagCalibration('cMVAv2', 'cMVAv2_Moriond17_B_H.csv')
# making a std::vector<std::string>> in python is a bit awkward,
# but works with root (needed to load other sys types):
v_sys = getattr(ROOT, 'vector<string>')()
v_sys.push_back('up')
v_sys.push_back('down')
# make a reader instance and load the sf data
readerLoose = ROOT.BTagCalibrationReader(
    0,              # 0 is for loose op, 1: medium, 2: tight, 3: discr. reshaping
    "central",      # central systematic type
    v_sys,          # vector of other sys. types
)
# for FLAV_B
readerLoose.load(
    calib,
    0,          # 0 is for b flavour, 1: FLAV_C, 2: FLAV_UDSG
    "ttbar"      # measurement type
)
# for FLAV_C
readerLoose.load(
    calib,
    1,          # 0 is for b flavour, 1: FLAV_C, 2: FLAV_UDSG
    "ttbar"      # measurement type
)
# for FLAV_UDSG
readerLoose.load(
    calib,
    2,          # 0 is for b flavour, 1: FLAV_C, 2: FLAV_UDSG
    "incl"      # measurement type
)

# make a reader instance and load the sf data
readerMed = ROOT.BTagCalibrationReader(
    1,              # 0 is for loose op, 1: medium, 2: tight, 3: discr. reshaping
    "central",      # central systematic type
    v_sys,          # vector of other sys. types
)
# for FLAV_B
readerMed.load(
    calib,
    0,          # 0 is for b flavour, 1: FLAV_C, 2: FLAV_UDSG
    "ttbar"      # measurement type
)
# for FLAV_C
readerMed.load(
    calib,
    1,          # 0 is for b flavour, 1: FLAV_C, 2: FLAV_UDSG
    "ttbar"      # measurement type
)
# for FLAV_UDSG
readerMed.load(
    calib,
    2,          # 0 is for b flavour, 1: FLAV_C, 2: FLAV_UDSG
    "incl"      # measurement type
)
##########################################################################################
#################      SETUP OPTIONS - File, Normalization, etc    #######################
##########################################################################################

# Input Options - file, cross-section, number of events
parser = ArgumentParser()
parser.add_argument("-f", "--file", dest="filename", help="input root file", metavar="FILE")
parser.add_argument("-b", "--batch", dest="dobatch", help="run in batch mode", metavar="BATCH")
parser.add_argument("-s", "--sigma", dest="crosssection", help="specify the process cross-section", metavar="SIGMA")
parser.add_argument("-n", "--ntotal", dest="ntotal", help="total number of MC events for the sample", metavar="NTOTAL")
parser.add_argument("-l", "--lumi", dest="lumi", help="integrated luminosity for data taking", metavar="LUMI")
parser.add_argument("-j", "--json", dest="json", help="json file for certified run:lumis", metavar="JSON")
parser.add_argument("-d", "--dir", dest="dir", help="output directory", metavar="DIR")
parser.add_argument("-p", "--pdf", dest="pdf", help="option to produce pdf uncertainties", metavar="PDF")
parser.add_argument("-y", "--year", dest="year", help="option to pick running year (2016,2017,2018)", metavar="YEAR")


options = parser.parse_args()
dopdf = int(options.pdf)==1
_year = options.year

# Here we get the file name, and adjust it accordingly for EOS, castor, or local directory
name = options.filename
amcNLOname = options.filename

if '/store' in name:
	#name = 'root://eoscms//eos/cms'+name
	name = '/eos/cms'+name
if '/castor/cern.ch' in name:
	name = 'rfio://'+name

# These are switches based on the tag name.
# Turn of the isolation condition for QCD studies
nonisoswitch=False
if "NonIso" in options.dir:
	nonisoswitch = True
# Quick test means no systematics
quicktestswitch = False
if "QuickTest" in options.dir:
	quicktestswitch = True
# Modifications of muon pT due to muon aligment mismodelling.
alignementcorrswitch = False
if "AlignmentCorr" in options.dir:
	alignementcorrswitch = True

print 'NonIso Switch = ', nonisoswitch
print 'Quick Switch (No Sys) = ', quicktestswitch
print 'AlignmentCorr Switch = ', alignementcorrswitch

# Get the file, tree, and number of entries
print name

fin = TFile.Open(name,"READ")

hev = fin.Get('EventCounter')
NORIG = hev.GetBinContent(1)
topPtReweightSwitch = False
if "TopPtReweight" in options.dir:
	print 'Aplying top pt reweight systematic!!!!!'
	topPtReweightSwitch = True
SumOfTopPtReweights = 1.0
_TopPtFactor = 1.0
#apply top pt-reweighting only if requested
if topPtReweightSwitch:
	SumOfTopPtReweights = hev.GetBinContent(4)
	_TopPtFactor = float(NORIG)/float(SumOfTopPtReweights)
if 'SingleMuon' in name or 'SingleElectron' in name or 'DoubleMuon' in name or 'DoubleEG' in name:
	_TopPtFactor = 1.0
#else:
#	_TopPtFactor = float(NORIG)/float(SumOfTopPtReweights)
# Typical event weight, sigma*lumi/Ngenerated
startingweight = _TopPtFactor*float(options.crosssection)*float(options.lumi)/float(options.ntotal)

#to = fin.Get("rootTupleTree/tree")
#No = t.GetEntries()
t = fin.Get("Events")
N = t.GetEntries()

# Here we are going to pre-skim the file to reduce running time.
indicator = ((name.split('/'))[-1]).replace('.root','')
#print indicator

# At least one 44 GeV Muon - offline cut is 50
#fj1 = TFile.Open(junkfile1,'RECREATE')
#t1 = to.CopyTree('MuonPt[]>12')#fixme was MuonPt[]>44
# t1 = to.CopyTree('(1)')
#Nm1 = t1.GetEntries()

#junkfile2 = str(randint(100000000,1000000000))+indicator+'junk.root'

# At least one 44 GeV jet - offline cut is 50
#fj2 = TFile.Open(junkfile2,'RECREATE')
#t = to.CopyTree('PFJetPtAK4CHS[]>18')#fixme was 44
#N = t.GetEntries()

# Print the reduction status
#print 'Original events:          ',No
#print 'After demand 1 pT16 muon or electron: ',Nm1
#print 'After demand 1 pT18 jet:  ',N

print 'Number of events:',N


##########################################################################################
#################      PREPARE THE VARIABLES FOR THE OUTPUT TREE   #######################
##########################################################################################

# Branches will be created as follows: One branch for each kinematic variable for each
# systematic variation determined in _variations. One branch for each weight and flag.
# So branch names will include weight_central, run_number, Pt_muon1, Pt_muon1MESUP, etc.

_kinematicvariables = ['Pt_muon1','Pt_muon2','Pt_ele1','Pt_ele2','Pt_jet1','Pt_jet2','Pt_miss']
_kinematicvariables += ['Pt_jet3','Pt_jet4']
_kinematicvariables += ['Eta_muon1','Eta_muon2','Eta_ele1','Eta_ele2','Eta_jet1','Eta_jet2']
_kinematicvariables += ['Phi_muon1','Phi_muon2','Phi_ele1','Phi_ele2','Phi_jet1','Phi_jet2','Phi_miss']
_kinematicvariables += ['Phi_Hjet1','Phi_Hjet2','Phi_Zjet1','Phi_Zjet2']
_kinematicvariables += ['Eta_Hjet1','Eta_Hjet2','Eta_Zjet1','Eta_Zjet2']
_kinematicvariables += ['Pt_muon1_gen','Pt_muon2_gen']
_kinematicvariables += ['Pt_Hjet1_gen','Pt_Hjet2_gen','Pt_Zjet1_gen','Pt_Zjet2_gen']
_kinematicvariables += ['Phi_Hjet1_gen','Phi_Hjet2_gen','Phi_Zjet1_gen','Phi_Zjet2_gen']
_kinematicvariables += ['Eta_Hjet1_gen','Eta_Hjet2_gen','Eta_Zjet1_gen','Eta_Zjet2_gen']
_kinematicvariables += ['Pt_muon1_genMatched','Pt_muon2_genMatched']
_kinematicvariables += ['Pt_Hjet1_genMatched','Pt_Hjet2_genMatched','Pt_Zjet1_genMatched','Pt_Zjet2_genMatched']

_kinematicvariables += ['AK8_Pt_recojet1'] #first jet in the pf jet collection
_kinematicvariables += ['AK8_Pt_Hjet_genMatched','AK8_Pt_Zjet_genMatched']
_kinematicvariables += ['AK8_Eta_Hjet_genMatched','AK8_Eta_Zjet_genMatched']
_kinematicvariables += ['AK8_Phi_Hjet_genMatched','AK8_Phi_Zjet_genMatched']
_kinematicvariables += ['AK8_Mass_Hjet_genMatched','AK8_Mass_Zjet_genMatched']
_kinematicvariables += ['AK8_dRujH_genMatched','AK8_dRujZ_genMatched','AK8_dRujH_gen','AK8_dRujZ_gen']
_kinematicvariables += ['AK8_CSV_Hjet_genMatched','AK8_CSV_Zjet_genMatched']
_kinematicvariables += ['AK8_bdt_discr_H','AK8_bdt_discr_Z']
_kinematicvariables += ['AK8_Pt_Hjet','AK8_Pt_Zjet','AK8_mass_Hjet','AK8_mass_Zjet']
_kinematicvariables += ['AK8_Pt_Hjet_Matched','AK8_Pt_Zjet_Matched','AK8_mass_Hjet_Matched','AK8_mass_Zjet_Matched']
_kinematicvariables += ['AK8_M_uu4j','AK8_M_ee4j']
_kinematicvariables += ['AK8_Mbb_H','AK8_Mjj_Z']
_kinematicvariables += ['AK8_Mbb_H_genMatched','AK8_Mjj_Z_genMatched']
_kinematicvariables += ['AK8_DR_u1Hj','AK8_DR_u2Hj']
_kinematicvariables += ['AK8_DR_u1Zj','AK8_DR_u2Zj']
_kinematicvariables += ['AK8_DR_u1Hj_genMatched','AK8_DR_u2Hj_genMatched']
_kinematicvariables += ['AK8_DR_u1Zj_genMatched','AK8_DR_u2Zj_genMatched']
_kinematicvariables += ['AK8_DR_e1Hj','AK8_DR_e2Hj']
_kinematicvariables += ['AK8_DR_e1Zj','AK8_DR_e2Zj']
_kinematicvariables += ['AK8_DR_e1Hj_genMatched','AK8_DR_e2Hj_genMatched']
_kinematicvariables += ['AK8_DR_e1Zj_genMatched','AK8_DR_e2Zj_genMatched']
_kinematicvariables += ['AK8_DR_uu_bb_H','AK8_DR_uu_jj_Z','AK8_DPhi_uu_bb_H','AK8_DPhi_uu_jj_Z']
_kinematicvariables += ['AK8_DR_ee_bb_H','AK8_DR_ee_jj_Z','AK8_DPhi_ee_bb_H','AK8_DPhi_ee_jj_Z']
_kinematicvariables += ['AK8_M_uu4j_genMatched']
_kinematicvariables += ['AK8_M_ee4j_genMatched']

_kinematicvariables += ['X_miss','Y_miss']
_kinematicvariables += ['TrkIso_muon1','TrkIso_muon2','TrkIso_ele1','TrkIso_ele2']
_kinematicvariables += ['Charge_muon1','Charge_muon2','Charge_ele1','Charge_ele2']
_kinematicvariables += ['TrkGlbDpt_muon1','TrkGlbDpt_muon2']
_kinematicvariables += ['St_uu4j','St_ee4j']
_kinematicvariables += ['M_uu','M_ee']
_kinematicvariables += ['M_jj']
_kinematicvariables += ['DR_muon1muon2','DPhi_muon1met']#,'DPhi_jet1met','DPhi_jet2met']
_kinematicvariables += ['DR_ele1ele2','DPhi_ele1met']
_kinematicvariables += ['M_uujj','M_eejj']
_kinematicvariables += ['M_uu4j','M_ee4j']
_kinematicvariables += ['Mbb_H','Mjj_Z','Mjj_Z_3jet']
_kinematicvariables += ['Mbb_H_gen','Mjj_Z_gen']
_kinematicvariables += ['Mbb_H_genMatched','Mjj_Z_genMatched']
_kinematicvariables += ['Mbb_H_noReg','Muu4j_noReg']
_kinematicvariables += ['cosThetaStarMu','cosThetaStarEle']
_kinematicvariables += ['cosThetaStarMu_gen','cosThetaStarEle_gen']
_kinematicvariables += ['cosThetaStar_uu_gen','cosTheta_hbb_uu_gen','cosTheta_zjj_hzz_uu_gen','cosTheta_zuu_hzz_uu_gen','cosTheta_zj1_hzz_uu_gen','cosTheta_zu1_hzz_uu_gen']
_kinematicvariables += ['cosThetaStar_ee_gen','cosTheta_hbb_ee_gen','cosTheta_zjj_hzz_ee_gen','cosTheta_zee_hzz_ee_gen','cosTheta_zj1_hzz_ee_gen','cosTheta_ze1_hzz_ee_gen']
_kinematicvariables += ['phi0_uu_gen','phi1_uu_gen']
_kinematicvariables += ['phi0_ee_gen','phi1_ee_gen']
_kinematicvariables += ['cosThetaStarZuu_CS_gen','cosTheta_Zuu_gen']
_kinematicvariables += ['cosThetaStarZee_CS_gen','cosTheta_Zee_gen']
_kinematicvariables += ['phi0_zz_uu_gen','phi1_zuu_gen','phi1_zjj_uu_gen']
_kinematicvariables += ['phi0_zz_ee_gen','phi1_zuu_gen','phi1_zjj_ee_gen']
_kinematicvariables += ['cosThetaStar_uu','cosTheta_hbb_uu','cosTheta_zjj_hzz_uu','cosTheta_zuu_hzz','cosTheta_zj1_hzz_uu','cosTheta_zu1_hzz']
_kinematicvariables += ['cosThetaStar_ee','cosTheta_hbb_ee','cosTheta_zjj_hzz_ee','cosTheta_zee_hzz','cosTheta_zj1_hzz_ee','cosTheta_ze1_hzz']
_kinematicvariables += ['phi0_uu','phi1_uu']
_kinematicvariables += ['phi0_ee','phi1_ee']
_kinematicvariables += ['cosThetaStarZuu_CS','cosTheta_Zuu']
_kinematicvariables += ['cosThetaStarZee_CS','cosTheta_Zee']
_kinematicvariables += ['phi0_zz_uu','phi1_zuu','phi1_zjj_uu']
_kinematicvariables += ['phi0_zz_ee','phi1_zee','phi1_zjj_ee']
_kinematicvariables += ['Pt_Hjet1_noReg','Pt_Hjet2_noReg']
_kinematicvariables += ['Pt_Hjet1','Pt_Hjet2','Pt_Zjet1','Pt_Zjet2']
_kinematicvariables += ['Pt_Hjets','Pt_Zjets','Pt_uu','Pt_ee']
_kinematicvariables += ['DR_jj_Z','DR_bb_H']
_kinematicvariables += ['DR_u1Hj1','DR_u1Hj2','DR_u2Hj1','DR_u2Hj2']
_kinematicvariables += ['DR_u1Zj1','DR_u1Zj2','DR_u2Zj1','DR_u2Zj2']
_kinematicvariables += ['DR_u1Hj1_gen','DR_u1Hj2_gen','DR_u2Hj1_gen','DR_u2Hj2_gen']
_kinematicvariables += ['DR_u1Zj1_gen','DR_u1Zj2_gen','DR_u2Zj1_gen','DR_u2Zj2_gen']
_kinematicvariables += ['DR_u1Hj1_genMatched','DR_u1Hj2_genMatched','DR_u2Hj1_genMatched','DR_u2Hj2_genMatched']
_kinematicvariables += ['DR_u1Zj1_genMatched','DR_u1Zj2_genMatched','DR_u2Zj1_genMatched','DR_u2Zj2_genMatched']
_kinematicvariables += ['DR_e1Hj1','DR_e1Hj2','DR_e2Hj1','DR_e2Hj2']
_kinematicvariables += ['DR_e1Zj1','DR_e1Zj2','DR_e2Zj1','DR_e2Zj2']
_kinematicvariables += ['DR_e1Hj1_gen','DR_e1Hj2_gen','DR_e2Hj1_gen','DR_e2Hj2_gen']
_kinematicvariables += ['DR_e1Zj1_gen','DR_e1Zj2_gen','DR_e2Zj1_gen','DR_e2Zj2_gen']
_kinematicvariables += ['DR_e1Hj1_genMatched','DR_e1Hj2_genMatched','DR_e2Hj1_genMatched','DR_e2Hj2_genMatched']
_kinematicvariables += ['DR_e1Zj1_genMatched','DR_e1Zj2_genMatched','DR_e2Zj1_genMatched','DR_e2Zj2_genMatched']
_kinematicvariables += ['DR_uu_bb_H','DR_uu_jj_Z','DPhi_uu_bb_H','DPhi_uu_jj_Z']
_kinematicvariables += ['DR_ee_bb_H','DR_ee_jj_Z','DPhi_ee_bb_H','DPhi_ee_jj_Z']
_kinematicvariables += ['DPhi_jj_Z','DPhi_bb_H']
_kinematicvariables += ['M_uu4j_gen','M_uu4j_genMatched']
_kinematicvariables += ['M_ee4j_gen','M_ee4j_genMatched']
_kinematicvariables += ['jetCntPreFilter','JetCount','MuonCount','ElectronCount','GenJetCount']
_kinematicvariables += ['muonIndex1','muonIndex2']
_kinematicvariables += ['ptHat']
_kinematicvariables += ['CMVA_Zjet1','CMVA_Zjet2']
_kinematicvariables += ['CMVA_bjet1','CMVA_bjet2']
_kinematicvariables += ['Hjet1BsfLoose','Hjet1BsfLooseUp','Hjet1BsfLooseDown']
_kinematicvariables += ['Hjet1BsfMedium','Hjet1BsfMediumUp','Hjet1BsfMediumDown']
_kinematicvariables += ['Hjet2BsfLoose','Hjet2BsfLooseUp','Hjet2BsfLooseDown']
_kinematicvariables += ['Hjet2BsfMedium','Hjet2BsfMediumUp','Hjet2BsfMediumDown']
_kinematicvariables += ['Zjet1BsfLoose','Zjet1BsfLooseUp','Zjet1BsfLooseDown']
_kinematicvariables += ['Zjet1BsfMedium','Zjet1BsfMediumUp','Zjet1BsfMediumDown']
_kinematicvariables += ['Zjet2BsfLoose','Zjet2BsfLooseUp','Zjet2BsfLooseDown']
_kinematicvariables += ['Zjet2BsfMedium','Zjet2BsfMediumUp','Zjet2BsfMediumDown']
_kinematicvariables += ['ele1IDandIsoSF','ele2IDandIsoSF']
_kinematicvariables += ['ele1IDandIsoSFup','ele2IDandIsoSFup']
_kinematicvariables += ['ele1IDandIsoSFdown','ele2IDandIsoSFdown']
_kinematicvariables += ['ele1hltSF','ele1hltSFUp','ele1hltSFDown']
_kinematicvariables += ['ele2hltSF','ele2hltSFUp','ele2hltSFDown']
_kinematicvariables += ['isMuonEvent','isElectronEvent']
_kinematicvariables += ['isElectronEvent_gen','isMuonEvent_gen','isTauEvent_gen']
_kinematicvariables += ['Hj1Matched','Hj2Matched','Zj1Matched','Zj2Matched']
_kinematicvariables += ['Hj1Present','Hj2Present','Zj1Present','Zj2Present']
_kinematicvariables += ['NGenMuonsZ', 'NGenElecsZ']
_kinematicvariables += ['M_uujj_gen', 'M_uujj_genMatched']
_kinematicvariables += ['M_eejj_gen', 'M_eejj_genMatched']
_kinematicvariables += ['M_uu_gen', 'M_uu_genMatched']
_kinematicvariables += ['M_ee_gen', 'M_ee_genMatched']
_kinematicvariables += ['bscoreMVA1_genMatched', 'bscoreMVA2_genMatched']
_kinematicvariables += ['CorHj1j2Avail','CorZj1j2Avail']
_kinematicvariables += ['WorZSystemPt']

_kinematicvariables += ['uu_s0_bdt_discrim_M260','uu_s0_bdt_discrim_M270','uu_s0_bdt_discrim_M300','uu_s0_bdt_discrim_M350','uu_s0_bdt_discrim_M400']
_kinematicvariables += ['uu_s0_bdt_discrim_M450','uu_s0_bdt_discrim_M500','uu_s0_bdt_discrim_M550','uu_s0_bdt_discrim_M600','uu_s0_bdt_discrim_M650']
_kinematicvariables += ['uu_s0_bdt_discrim_M750','uu_s0_bdt_discrim_M800','uu_s0_bdt_discrim_M900','uu_s0_bdt_discrim_M1000']
_kinematicvariables += ['ee_s0_bdt_discrim_M260','ee_s0_bdt_discrim_M270','ee_s0_bdt_discrim_M300','ee_s0_bdt_discrim_M350','ee_s0_bdt_discrim_M400']
_kinematicvariables += ['ee_s0_bdt_discrim_M450','ee_s0_bdt_discrim_M500','ee_s0_bdt_discrim_M550','ee_s0_bdt_discrim_M600','ee_s0_bdt_discrim_M650']
_kinematicvariables += ['ee_s0_bdt_discrim_M750','ee_s0_bdt_discrim_M800','ee_s0_bdt_discrim_M900','ee_s0_bdt_discrim_M1000']
_kinematicvariables += ['uu_s2_bdt_discrim_M260','uu_s2_bdt_discrim_M270','uu_s2_bdt_discrim_M300','uu_s2_bdt_discrim_M350','uu_s2_bdt_discrim_M400']
_kinematicvariables += ['uu_s2_bdt_discrim_M450','uu_s2_bdt_discrim_M500','uu_s2_bdt_discrim_M550','uu_s2_bdt_discrim_M600','uu_s2_bdt_discrim_M650']
_kinematicvariables += ['uu_s2_bdt_discrim_M750','uu_s2_bdt_discrim_M800','uu_s2_bdt_discrim_M900','uu_s2_bdt_discrim_M1000']
_kinematicvariables += ['ee_s2_bdt_discrim_M260','ee_s2_bdt_discrim_M270','ee_s2_bdt_discrim_M300','ee_s2_bdt_discrim_M350','ee_s2_bdt_discrim_M400']
_kinematicvariables += ['ee_s2_bdt_discrim_M450','ee_s2_bdt_discrim_M500','ee_s2_bdt_discrim_M550','ee_s2_bdt_discrim_M600','ee_s2_bdt_discrim_M650']
_kinematicvariables += ['ee_s2_bdt_discrim_M750','ee_s2_bdt_discrim_M800','ee_s2_bdt_discrim_M900','ee_s2_bdt_discrim_M1000']

_kinematicvariables_systOnly = ['uu_s0_bdt_discrim_M260','uu_s0_bdt_discrim_M270','uu_s0_bdt_discrim_M300','uu_s0_bdt_discrim_M350','uu_s0_bdt_discrim_M400']
_kinematicvariables_systOnly += ['uu_s0_bdt_discrim_M450','uu_s0_bdt_discrim_M500','uu_s0_bdt_discrim_M550','uu_s0_bdt_discrim_M600','uu_s0_bdt_discrim_M650']
_kinematicvariables_systOnly += ['uu_s0_bdt_discrim_M750','uu_s0_bdt_discrim_M800','uu_s0_bdt_discrim_M900','uu_s0_bdt_discrim_M1000']
_kinematicvariables_systOnly += ['ee_s0_bdt_discrim_M260','ee_s0_bdt_discrim_M270','ee_s0_bdt_discrim_M300','ee_s0_bdt_discrim_M350','ee_s0_bdt_discrim_M400']
_kinematicvariables_systOnly += ['ee_s0_bdt_discrim_M450','ee_s0_bdt_discrim_M500','ee_s0_bdt_discrim_M550','ee_s0_bdt_discrim_M600','ee_s0_bdt_discrim_M650']
_kinematicvariables_systOnly += ['ee_s0_bdt_discrim_M750','ee_s0_bdt_discrim_M800','ee_s0_bdt_discrim_M900','ee_s0_bdt_discrim_M1000']
_kinematicvariables_systOnly += ['uu_s2_bdt_discrim_M260','uu_s2_bdt_discrim_M270','uu_s2_bdt_discrim_M300','uu_s2_bdt_discrim_M350','uu_s2_bdt_discrim_M400']
_kinematicvariables_systOnly += ['uu_s2_bdt_discrim_M450','uu_s2_bdt_discrim_M500','uu_s2_bdt_discrim_M550','uu_s2_bdt_discrim_M600','uu_s2_bdt_discrim_M650']
_kinematicvariables_systOnly += ['uu_s2_bdt_discrim_M750','uu_s2_bdt_discrim_M800','uu_s2_bdt_discrim_M900','uu_s2_bdt_discrim_M1000']
_kinematicvariables_systOnly += ['ee_s2_bdt_discrim_M260','ee_s2_bdt_discrim_M270','ee_s2_bdt_discrim_M300','ee_s2_bdt_discrim_M350','ee_s2_bdt_discrim_M400']
_kinematicvariables_systOnly += ['ee_s2_bdt_discrim_M450','ee_s2_bdt_discrim_M500','ee_s2_bdt_discrim_M550','ee_s2_bdt_discrim_M600','ee_s2_bdt_discrim_M650']
_kinematicvariables_systOnly += ['ee_s2_bdt_discrim_M750','ee_s2_bdt_discrim_M800','ee_s2_bdt_discrim_M900','ee_s2_bdt_discrim_M1000']

#_weights = ['scaleWeight_Up','scaleWeight_Down','scaleWeight_R1_F1','scaleWeight_R1_F2','scaleWeight_R1_F0p5','scaleWeight_R2_F1','scaleWeight_R2_F2','scaleWeight_R2_F0p5','scaleWeight_R0p5_F1','scaleWeight_R0p5_F2','scaleWeight_R0p5_F0p5','scaleWeight_R2_F2','weight_amcNLO','weight_nopu','weight_central', 'weight_pu_up', 'weight_pu_down','weight_topPt']
#removing weight_amcNLO (always 0 anyway)
_weights = ['scaleWeight_Up','scaleWeight_Down','scaleWeight_R1_F1','scaleWeight_R1_F2','scaleWeight_R1_F0p5','scaleWeight_R2_F1','scaleWeight_R2_F2','scaleWeight_R2_F0p5','scaleWeight_R0p5_F1','scaleWeight_R0p5_F2','scaleWeight_R0p5_F0p5','scaleWeight_R2_F2','weight_nopu','weight_central', 'weight_pu_up', 'weight_pu_down','weight_topPt','prefireWeight','prefireWeight_up','prefireWeight_down']
_flagDoubles = ['run_number','event_number','lumi_number']
##_flags = ['Flag_HLT_Ele27_WPTight_Gsf','GoodVertexCount','passTriggerObjectMatching']
_flags = ['Flag_HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ','Flag_HLT_Ele27_WPTight_Gsf','GoodVertexCount','passTriggerObjectMatching','pass_HLT_Mu17_Mu8']
_flags += ['passDataCert']
##_flags += ['Flag_PrimaryVertex','passDataCert']
_flags += ['Flag_BadChargedCandidateFilter','Flag_BadChargedCandidateSummer16Filter','Flag_BadGlobalMuon','Flag_BadPFMuonFilter','Flag_BadPFMuonSummer16Filter','Flag_CSCTightHalo2015Filter','Flag_CSCTightHaloFilter','Flag_CSCTightHaloTrkMuUnvetoFilter','Flag_EcalDeadCellBoundaryEnergyFilter','Flag_EcalDeadCellTriggerPrimitiveFilter','Flag_HBHENoiseFilter','Flag_HBHENoiseIsoFilter','Flag_HcalStripHaloFilter','Flag_METFilters','Flag_chargedHadronTrackResolutionFilter','Flag_ecalBadCalibFilter','Flag_ecalBadCalibFilterV2','Flag_ecalLaserCorrFilter','Flag_eeBadScFilter','Flag_globalSuperTightHalo2016Filter','Flag_globalTightHalo2016Filter','Flag_goodVertices','Flag_hcalLaserEventFilter','Flag_muonBadTrackFilter','Flag_trkPOGFilters','Flag_trkPOG_logErrorTooManyClusters','Flag_trkPOG_manystripclus53X','Flag_trkPOG_toomanystripclus53X']
#_variations = ['','JESup','JESdown','MESup','MESdown','JERup','JERdown','MER']
#_variations = ['','JESup','JESdown','JERup','JERdown','MESup','MESdown','MER']#,'EESup','EESdown','EER']
_variations = ['','JESup','JESdown','JESAbsoluteMPFBiasUp','JESAbsoluteMPFBiasDown','JESAbsoluteScaleUp','JESAbsoluteScaleDown','JESAbsoluteStatUp','JESAbsoluteStatDown','JESFlavorQCDUp','JESFlavorQCDDown','JESFragmentationUp','JESFragmentationDown','JESPileUpDataMCUp','JESPileUpDataMCDown','JESPileUpPtBBUp','JESPileUpPtBBDown','JESPileUpPtEC1Up','JESPileUpPtEC1Down','JESPileUpPtEC2Up','JESPileUpPtEC2Down','JESPileUpPtHFUp','JESPileUpPtHFDown','JESPileUpPtRefUp','JESPileUpPtRefDown','JESRelativeBalUp','JESRelativeBalDown','JESRelativeFSRUp','JESRelativeFSRDown','JESRelativeJEREC1Up','JESRelativeJEREC1Down','JESRelativeJEREC2Up','JESRelativeJEREC2Down','JESRelativeJERHFUp','JESRelativeJERHFDown','JESRelativePtBBUp','JESRelativePtBBDown','JESRelativePtEC1Up','JESRelativePtEC1Down','JESRelativePtEC2Up','JESRelativePtEC2Down','JESRelativePtHFUp','JESRelativePtHFDown','JESRelativeStatECUp','JESRelativeStatECDown','JESRelativeStatFSRUp','JESRelativeStatFSRDown','JESRelativeStatHFUp','JESRelativeStatHFDown','JESSinglePionECALUp','JESSinglePionECALDown','JESSinglePionHCALUp','JESSinglePionHCALDown','JESTimePtEtaUp','JESTimePtEtaDown','JERup','JERdown']#,'MESup','MESdown','MER','EESup','EESdown','EER']
if nonisoswitch==True or quicktestswitch==True:
	print 'NOT performing systematics...'
	_variations = ['']  # For quicker tests
# _variations = ['']  # For quicker tests



##########################################################################################
#################     Everything needed for Pileup reweighting     #######################
##########################################################################################



def GetPURescalingFactors(puversion):
	# Purpose: To get the pileup reweight factors from the PU_Central.root, PU_Up.root, and PU_Down.root files.
	#         The MC Truth distribution is taken from https://twiki.cern.ch/twiki/bin/view/CMS/PileupMCReweightingUtilities

	#MCDistSummer12 = [2.560E-06, 5.239E-06, 1.420E-05, 5.005E-05, 1.001E-04, 2.705E-04, 1.999E-03, 6.097E-03, 1.046E-02, 1.383E-02,
        #              1.685E-02, 2.055E-02, 2.572E-02, 3.262E-02, 4.121E-02, 4.977E-02, 5.539E-02, 5.725E-02, 5.607E-02, 5.312E-02, 5.008E-02, 4.763E-02,
        #              4.558E-02, 4.363E-02, 4.159E-02, 3.933E-02, 3.681E-02, 3.406E-02, 3.116E-02, 2.818E-02, 2.519E-02, 2.226E-02, 1.946E-02, 1.682E-02,
        #              1.437E-02, 1.215E-02, 1.016E-02, 8.400E-03, 6.873E-03, 5.564E-03, 4.457E-03, 3.533E-03, 2.772E-03, 2.154E-03, 1.656E-03, 1.261E-03,
        #              9.513E-04, 7.107E-04, 5.259E-04, 3.856E-04, 2.801E-04, 2.017E-04, 1.439E-04, 1.017E-04, 7.126E-05, 4.948E-05, 3.405E-05, 2.322E-05,
        #              1.570E-05, 5.005E-06]

	#MCDistStartup15 = [4.8551E-07,1.74806E-06,3.30868E-06,1.62972E-05,4.95667E-05,0.000606966,0.003307249,0.010340741,0.022852296,0.041948781,0.058609363,0.067475755,0.072817826,0.075931405,0.076782504,0.076202319,0.074502547,0.072355135,0.069642102,0.064920999,0.05725576,0.047289348,0.036528446,0.026376131,0.017806872,0.011249422,0.006643385,0.003662904,0.001899681,0.00095614,0.00050028,0.000297353,0.000208717,0.000165856,0.000139974,0.000120481,0.000103826,8.88868E-05,7.53323E-05,6.30863E-05,5.21356E-05,4.24754E-05,3.40876E-05,2.69282E-05,2.09267E-05,1.5989E-05,4.8551E-06,2.42755E-06,4.8551E-07,2.42755E-07,1.21378E-07,4.8551E-08]#fixme todo updated to 2015, from https://github.com/cms-sw/cmssw/blob/CMSSW_7_6_X/SimGeneral/MixingModule/python/mix_2015_25ns_Startup_PoissonOOTPU_cfi.py and https://twiki.cern.ch/twiki/bin/view/CMS/PdmVPileUpDescription#Run_2_and_Upgrades

	#MCDistStartup16 = [0.000829312873542,0.00124276120498,0.00339329181587,0.00408224735376,0.00383036590008,0.00659159288946,0.00816022734493,0.00943640833116,0.0137777376066,0.017059392038,0.0213193035468,0.0247343174676,0.0280848773878,0.0323308476564,0.0370394341409,0.0456917721191,0.0558762890594,0.0576956187107,0.0625325287017,0.0591603758776,0.0656650815128,0.0678329011676,0.0625142146389,0.0548068448797,0.0503893295063,0.040209818868,0.0374446988111,0.0299661572042,0.0272024759921,0.0219328403791,0.0179586571619,0.0142926728247,0.00839941654725,0.00522366397213,0.00224457976761,0.000779274977993,0.000197066585944,7.16031761328e-05,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0]#Updated to 2016, from https://github.com/cms-sw/cmssw/blob/CMSSW_8_0_X/SimGeneral/MixingModule/python/mix_2016_25ns_SpringMC_PUScenarioV1_PoissonOOTPU_cfi.py and https://twiki.cern.ch/twiki/bin/view/CMS/PdmVPileUpDescription#Run_2_and_Upgrades

	MCDistSummer16 = [1.78653e-05 ,2.56602e-05 ,5.27857e-05 ,8.88954e-05 ,0.000109362 ,0.000140973 ,0.000240998 ,0.00071209 ,0.00130121 ,0.00245255 ,0.00502589 ,0.00919534 ,0.0146697 ,0.0204126 ,0.0267586 ,0.0337697 ,0.0401478 ,0.0450159 ,0.0490577 ,0.0524855 ,0.0548159 ,0.0559937 ,0.0554468 ,0.0537687 ,0.0512055 ,0.0476713 ,0.0435312 ,0.0393107 ,0.0349812 ,0.0307413 ,0.0272425 ,0.0237115 ,0.0208329 ,0.0182459 ,0.0160712 ,0.0142498 ,0.012804 ,0.011571 ,0.010547 ,0.00959489 ,0.00891718 ,0.00829292 ,0.0076195 ,0.0069806 ,0.0062025 ,0.00546581 ,0.00484127 ,0.00407168 ,0.00337681 ,0.00269893 ,0.00212473 ,0.00160208 ,0.00117884 ,0.000859662 ,0.000569085 ,0.000365431 ,0.000243565 ,0.00015688 ,9.88128e-05 ,6.53783e-05 ,3.73924e-05 ,2.61382e-05 ,2.0307e-05 ,1.73032e-05 ,1.435e-05 ,1.36486e-05 ,1.35555e-05 ,1.37491e-05 ,1.34255e-05 ,1.33987e-05 ,1.34061e-05 ,1.34211e-05 ,1.34177e-05 ,1.32959e-05 ,1.33287e-05,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]# from https://twiki.cern.ch/twiki/bin/view/CMS/PdmV2016Analysis and https://github.com/cms-sw/cmssw/blob/CMSSW_8_0_X/SimGeneral/MixingModule/python/mix_2016_25ns_Moriond17MC_PoissonOOTPU_cfi.py


    # This is the standard (all of 2012) pileup scenario
	if puversion =='Basic':
		f_pu_up = TFile("PU_Up.root","read")
		h_pu_up = f_pu_up.Get('pileup')
		f_pu_down = TFile("PU_Down.root","read")
		h_pu_down = f_pu_down.Get('pileup')
		f_pu_central = TFile("PU_Central.root","read")
		h_pu_central = f_pu_central.Get('pileup')
		#h_pu_up = TFile.Open("PU_Up.root",'read').Get('pileup')
		#h_pu_down = TFile.Open("PU_Down.root",'read').Get('pileup')
		#h_pu_central = TFile("PU_Central.root",'read').Get('pileup')

	# This is just for 2012D. It was used for some studies. Not that important.
	#if puversion =='2012D':
	#	f_pu_up = TFile("PU_Up_2012D.root","read")
	#	h_pu_up = f_pu_up.Get('pileup')
	#	f_pu_down = TFile("PU_Down_2012D.root","read")
	#	h_pu_down = f_pu_down.Get('pileup')
	#	f_pu_central = TFile("PU_Central_2012D.root","read")
	#	h_pu_central = f_pu_central.Get('pileup')
	#	#h_pu_up = TFile.Open("PU_Up_2012D.root").Get('pileup')
	#	#h_pu_down = TFile.Open("PU_Down_2012D.root",'read').Get('pileup')
	#	#h_pu_central = TFile.Open("PU_Central_2012D.root",'read').Get('pileup')

	# Arrays for the central and up/down variation weights.
	bins_pu_central = []
	bins_pu_up = []
	bins_pu_down = []

	# Loop over bins and put content in arrays
	for x in range(h_pu_up.GetNbinsX()):
		bin = x +1
		bins_pu_central.append(h_pu_central.GetBinContent(bin))
		bins_pu_up.append(h_pu_up.GetBinContent(bin))
		bins_pu_down.append(h_pu_down.GetBinContent(bin))

	# Sum bins for proper normalizations
	total_pu_central = sum(bins_pu_central)
	total_pu_up = sum(bins_pu_up)
	total_pu_down = sum(bins_pu_down)
	total_mc = sum(MCDistSummer16)

	# Get normalized bins
	bins_pu_central_norm = [x/total_pu_central for x in bins_pu_central]
	bins_pu_up_norm = [x/total_pu_up for x in bins_pu_up]
	bins_pu_down_norm = [x/total_pu_down for x in bins_pu_down]
	bins_mc_norm  = [x/total_mc for x in MCDistSummer16]

	# Arrays for scale factors (central and systematic varied)
	scale_pu_central = []
	scale_pu_up = []
	scale_pu_down = []

	# Fill arrays of scale factors
	for x in range(len(bins_mc_norm)):
		if bins_mc_norm[x]>0:
			scale_pu_central.append(bins_pu_central_norm[x]/bins_mc_norm[x])
			scale_pu_up.append(bins_pu_up_norm[x]/bins_mc_norm[x])
			scale_pu_down.append(bins_pu_down_norm[x]/bins_mc_norm[x])
		else:
			scale_pu_central.append(1.)
			scale_pu_up.append(1.)
			scale_pu_down.append(1.)

	# Return arrays of scale factors
	return [scale_pu_central, scale_pu_up, scale_pu_down]

# Use the above function to get the pu weights
[CentralWeights,UpperWeights,LowerWeights] =GetPURescalingFactors('Basic')


##########################################################################################
#################     Everything needed for PDF Weight variation   #######################
##########################################################################################


def GetPDFWeightVars(T):
	# Purpose: Determine all the branch names needed to store the PDFWeights
	#         for CTEQ, MMTH, and NNPDF in flat (non vector) form.
	if T.run>1:
		return []
	else:
		T.GetEntry(1)
		pdfweights=[]
		#for x in range(len(T.PDFCTEQWeights)):
		#	#if(T.PDFCTEQWeights[x]>-10 and T.PDFCTEQWeights[x]<10): pdfweights.append('factor_cteq_'+str(x+1-53))
		#	if(T.PDFCTEQWeights[x]>-10 and T.PDFCTEQWeights[x]<10): pdfweights.append('factor_cteq_'+str(x+1))
		#for x in range(len(T.PDFMMTHWeights)):
		#	#if(T.PDFMMTHWeights[x]>-10 and T.PDFMMTHWeights[x]<10): pdfweights.append('factor_mmth_'+str(x+1-51))
		#	if(T.PDFMMTHWeights[x]>-10 and T.PDFMMTHWeights[x]<10): pdfweights.append('factor_mmth_'+str(x+1))
                #
		#for x in range(101):
		#	pdfweights.append('factor_nnpdf_'+str(x+1))
		#if 'amcatnlo' in amcNLOname :
		#	for x in range(len(T.PDFAmcNLOWeights)):
		#		pdfweights.append('factor_nnpdf_'+str(x+1))
		#else:
		#	for x in range(len(T.PDFNNPDFWeights)):
		#	        #if(T.PDFNNPDFWeights[x]>-10 and T.PDFNNPDFWeights[x]<10): pdfweights.append('factor_nnpdf_'+str(x+1-101))
		#	        #if(T.PDFNNPDFWeights[x]>-10 and T.PDFNNPDFWeights[x]<10): pdfweights.append('factor_nnpdf_'+str(x+1))
		#		if(T.PDFNNPDFWeights[x]>-10 and T.PDFNNPDFWeights[x]<10): pdfweights.append('factor_nnpdf_'+str(x+1))
                for x in range(len(T.LHEPdfWeight)):
			pdfweights.append('factor_pdf_'+str(x+1))

		return pdfweights


# Get the appropriate numbers of PDF weights from the tree
_pdfweightsnames = GetPDFWeightVars(t)

##########################################################################################
#################         Prepare the Output Tree                  #######################
##########################################################################################

# First create the output file.
tmpfout = str(randint(100000000,1000000000))+indicator+'.root'
if '/store' in name:
	finalfout = options.dir+'/'+(name.split('/')[-5]+'__'+name.split('/')[-1].replace('.root','_tree.root'))#changed -2 to -5 to get dataset name instead of 0000
else:
	finalfout = options.dir+'/'+name.replace('.root','_tree.root')

# Create the output file and tree "PhysicalVariables"
fout = TFile.Open(tmpfout,"RECREATE")
tout=TTree("PhysicalVariables","PhysicalVariables")


# Below all the branches are created, everything is a double except for flags
# for b in _kinematicvariables:
# 	for v in _variations:
# 		exec(b+v+' = array.array("f",[0])')
# 		exec('tout.Branch("'+b+v+'",'+b+v+',"'+b+v+'/F")' )
# for b in _weights:
# 	exec(b+' = array.array("f",[0])')
# 	exec('tout.Branch("'+b+'",'+b+',"'+b+'/F")' )
# if dopdf:
# 	for b in _pdfweights:
# 		exec(b+' = array.array("f",[0])')
# 		print (b+' = array.array("f",[0])')
# 		exec('tout.Branch("'+b+'",'+b+',"'+b+'/F")' )
# for b in _flags:
# 	exec(b+' = array.array("L",[0])')
# 	exec('tout.Branch("'+b+'",'+b+',"'+b+'/i")' )

Branches = {}
#for b in _kinematicvariables:
#	for v in _variations:
#		Branches[b+v] = array.array("f",[0])
#		tout.Branch(b+v,Branches[b+v],b+v+"/F")
#this is the baseline
for b in _kinematicvariables:
	Branches[b] = array.array("f",[0])
	tout.Branch(b,Branches[b],b+"/F")
#this is systematic variations
for b in _kinematicvariables_systOnly:
	for v in _variations:
		if v!='':
			Branches[b+v] = array.array("f",[0])
			tout.Branch(b+v,Branches[b+v],b+v+"/F")
for b in _weights:
	Branches[b] = array.array("f",[0])
	tout.Branch(b,Branches[b],b+"/F")
if dopdf:
	for b in _pdfweightsnames:
		Branches[b] = array.array("f",[0])
		tout.Branch(b,Branches[b],b+"/F")
for b in _flagDoubles:
	Branches[b] = array.array("f",[0])
	tout.Branch(b,Branches[b],b+"/F")

for b in _flags:
	Branches[b] = array.array("L",[0])
	tout.Branch(b,Branches[b],b+"/i")

##########################################################################################
#################      Setup BDT discrimator calculation           #######################
##########################################################################################
TMVA.Tools.Instance()
SignalM = ['260','270','300','350','400', '450', '500', '550', '600','650', '750', '800', '900', '1000']

# TMVA.Reader
#--- muon BDT
reader_22vars_uu = TMVA.Reader("!Color")
# the order of the variables matters, need to be the same as when training
_bdtvars_uu = ['Mbb_H','DR_bb_H','Mjj_Z','DR_jj_Z','M_uu','DR_muon1muon2','DR_uu_bb_H','DR_u1Hj1','DR_u1Hj2','DR_u2Hj1','DR_u2Hj2','DR_uu_jj_Z','DR_u1Zj1','DR_u1Zj2','DR_u2Zj1','DR_u2Zj2','abs(cosThetaStarMu)','abs(cosTheta_hbb_uu)','abs(cosTheta_zuu_hzz)','abs(DPhi_muon1met)','abs(phi1_uu)','abs(phi1_zjj_uu)']
_bdtvarnames_uu = {}
for vth in _bdtvars_uu:
	_bdtvarnames_uu[vth] = array.array('f',[0])
	reader_22vars_uu.AddVariable(vth, _bdtvarnames_uu[vth])
# TMVA.Reader booked with BDT_classifier, input is .weights.xml file
for ith in range(len(SignalM)):
	reader_22vars_uu.BookMVA(str("BDT_classifier_22vars_s0_uu_M" + SignalM[ith]), str("weights_classification/weights_file_22vars_s0_uu/TMVAClassification_BDT_M" + SignalM[ith] + ".weights.xml"))
	reader_22vars_uu.BookMVA(str("BDT_classifier_22vars_s2_uu_M" + SignalM[ith]), str("weights_classification/weights_file_22vars_s2_uu/TMVAClassification_BDT_M" + SignalM[ith] + ".weights.xml"))

#--- eletron BDT
reader_22vars_ee = TMVA.Reader("!Color")
_bdtvars_ee = ['Mbb_H','DR_bb_H','Mjj_Z','DR_jj_Z','M_ee','DR_ele1ele2','DR_ee_bb_H','DR_e1Hj1','DR_e1Hj2','DR_e2Hj1','DR_e2Hj2','DR_ee_jj_Z','DR_e1Zj1','DR_e1Zj2','DR_e2Zj1','DR_e2Zj2','abs(cosThetaStarEle)','abs(cosTheta_hbb_ee)','abs(cosTheta_zee_hzz)','abs(DPhi_ele1met)','abs(phi1_ee)','abs(phi1_zjj_ee)']
_bdtvarnames_ee = {}
for vth in _bdtvars_ee:
	_bdtvarnames_ee[vth] = array.array('f',[0])
	reader_22vars_ee.AddVariable(vth, _bdtvarnames_ee[vth])
for ith in range(len(SignalM)):
	reader_22vars_ee.BookMVA(str("BDT_classifier_22vars_s0_ee_M" + SignalM[ith]), str("weights_classification/weights_file_22vars_s0_ee/TMVAClassification_BDT_M" + SignalM[ith] + ".weights.xml"))
	reader_22vars_ee.BookMVA(str("BDT_classifier_22vars_s2_ee_M" + SignalM[ith]), str("weights_classification/weights_file_22vars_s2_ee/TMVAClassification_BDT_M" + SignalM[ith] + ".weights.xml"))



# TMVA.Reader
reader = TMVA.Reader("!Color")
# the order of the variables matters, need to be the same as when training
_bdtvars = ['AK8_Mass_Hjet_genMatched','AK8_dRujH_genMatched','AK8_Pt_Hjet_genMatched','AK8_Eta_Hjet_genMatched','AK8_Phi_Hjet_genMatched','AK8_CSV_Hjet_genMatched']
_bdtvarnames = {}
for vth in _bdtvars:
	_bdtvarnames[vth] = array.array('f',[0])
	reader.AddVariable(vth, _bdtvarnames[vth])
# TMVA.Reader booked with BDT_classifier, input is .weights.xml file
reader.BookMVA(str("BDT_classifier"), str("/afs/cern.ch/work/v/vinguyen/public/LQ2Analysis13TeV/weights/600GeV/TMVAClassification_ptu1u2cut_BDT.weights.xml"))
# TMVA.Reader
readerZ = TMVA.Reader("!Color")
# the order of the variables matters, need to be the same as when training
_bdtvarsZ = ['AK8_Mass_Zjet_genMatched','AK8_dRujZ_genMatched','AK8_Pt_Zjet_genMatched','AK8_Eta_Zjet_genMatched','AK8_Phi_Zjet_genMatched','AK8_CSV_Zjet_genMatched']
_bdtvarnamesZ = {}
for vth in _bdtvarsZ:
	_bdtvarnamesZ[vth] = array.array('f',[0])
	readerZ.AddVariable(vth, _bdtvarnamesZ[vth])
# TMVA.Reader booked with BDT_classifier, input is .weights.xml file
readerZ.BookMVA(str("BDT_classifier"), str("/afs/cern.ch/work/v/vinguyen/public/LQ2Analysis13TeV/weights/600GeV/TMVAClassification_ptu1u2cut_Zjets_BDT.weights.xml"))



##########################################################################################
#################           SPECIAL FUNCTIONS FOR ANALYSIS         #######################
##########################################################################################

def PrintBranchesAndExit(T):
	# Purpose: Just list the branches on the input file and bail out.
	#         For coding and debugging
	x = T.GetListOfBranches()
	for n in x:
		print n
	sys.exit()

# PrintBranchesAndExit(t)

#def parseRLElist(triples):
#	parsedTriples = []
#	tempTrips = []
#	_runs = []
#	_le = []
#	i = 0
#	for trip in triples :
#		[_r,_l,_e] = [trip[0],trip[1],trip[2]]
#		print [_r,_l,_e]
#		_runs.append[_r]
#		if triples[i+1][0] not in _runs :
#			_le.append([_l,_e])
#			parsedTriples.append([r,_le])
#			_le = []
#		else :
#			_le.append([_l,_e])
#		i = i+1
#	print parsedTriples
#	return parsedTriples
#
def GetRunLumiList():
	# Purpose: Parse the json file to get a list of good runs and lumis
	#          to call on later. For real data only.
	jfile = open(options.json,'r')
	flatjson = ''
	for line in jfile:
		flatjson+=line.replace('\n','')
	flatjson = flatjson.replace("}","")
	flatjson = flatjson.replace("{","")
	flatjson = flatjson.replace(":","")
	flatjson = flatjson.replace(" ","")
	flatjson = flatjson.replace("\t","")

	jinfo = flatjson.split('"')
	strjson = ''
	for j in jinfo:
		strjson += j
	strjson = strjson.replace('\n[',' [')
	strjson = strjson.replace(']],',']]\n')
	strjson = strjson.replace('[[',' [[')

	pairs = []
	for line in strjson.split('\n'):
		pair = []
		line = line.split(' ')
		exec('arun = '+line[0])
		exec('alumis = '+line[1])
		verboselumis = []
		for r in alumis:
			verboselumis +=  range(r[0],r[1]+1)

		pair.append(arun)
		pair.append(verboselumis)
		pairs.append(pair)
	return pairs

GoodRunLumis = GetRunLumiList()

def CheckRunLumiCert(r,l):
	# Purpose: Use the GoodRunLumis list, to check and see if a given
	#          run and lumi (r and l) are in the list.
	for _rl in GoodRunLumis:
		if _rl[0]==r:
			for _l in _rl[1]:
				if _l == l:
					return True
	return False
def TransMass(p1,p2):
	# Purpose: Simple calculation of transverse mass between two TLorentzVectors
	return math.sqrt( 2*p1.Pt()*p2.Pt()*(1-math.cos(p1.DeltaPhi(p2))) )

def ST(particles):
	# Purpose: Calculation of the scalar sum of PT of a set of TLorentzVectors
	st = 0.0
	for p in particles:
		st += p.Pt()
	return st

def PassTrigger(T,trigger_identifiers,prescale_threshold):
	# Purpose: Return a flag (1 or 0) to indicate whether the event passes any trigger
	#         which is syntactically matched to a set of strings trigger_identifiers,
	#         considering only triggers with a prescale <= the prescale threshold.
	for n in range(len(T.HLTInsideDatasetTriggerNames)):
		name = T.HLTInsideDatasetTriggerNames[n]
		#if 'Ele' in name or 'Pho' in name: print name, T.HLTInsideDatasetTriggerPrescales[n]
		consider_trigger=True
		for ident in trigger_identifiers:
			if ident not in name:
				consider_trigger=False
		if (consider_trigger==False) : continue

		prescale = T.HLTInsideDatasetTriggerPrescales[n]

		if prescale > prescale_threshold:
			consider_trigger=False
		if (consider_trigger==False) : continue

		decision = bool(T.HLTInsideDatasetTriggerDecisions[n])
		if decision==True:
			return 1
	return 0

def GetPUWeight(T,version,puversion):
	# Purpose: Get the pileup weight for an event. Version can indicate the central
	#         weight, or the Upper or Lower systematics. Needs to be updated for
	#         input PU histograms given only the generated disribution........

	# Only necessary for MC
	if T.run>1:
		return 1.0

	# Getting number of PU interactions, start with zero.
	N_pu = 0

	# Set N_pu to number of true PU interactions in the central bunch
	N_pu = int(1.0*(T.Pileup_nTrueInt))

	puweight = 0

	# Assign the list of possible PU weights according to what is being done
	# Central systematics Up, or systematic down
	if puversion=='Basic':
		puweights = CentralWeights
		if version=='SysUp':
			puweights=UpperWeights
		if version=='SysDown':
			puweights=LowerWeights

	# Also possible to do just for 2012D, for cross-checks.
	#if puversion=='2012D':
	#	puweights = CentralWeights_2012D
	#	if version=='SysUp':
	#		puweights=UpperWeights_2012D
	#	if version=='SysDown':
	#		puweights=LowerWeights_2012D


	# Make sure there exists a weight for the number of interactions given,
	# and set the puweight to the appropriate value.
	NRange = range(len(puweights))
	if N_pu in NRange:
		puweight=puweights[N_pu]
	# print puweight
	return puweight



def GetPDFWeights(T):
	# Purpose: Gather the pdf weights into a single list.
	_allweights = []
	#for x in range(len(T.PDFCTEQWeights)):
	#	if(T.PDFCTEQWeights[x]>-10 and T.PDFCTEQWeights[x]<10): _allweights.append(T.PDFCTEQWeights[x])
	#for x in range(len(T.PDFMMTHWeights)):
	#	if(T.PDFMMTHWeights[x]>-10 and T.PDFMMTHWeights[x]<10): _allweights.append(T.PDFMMTHWeights[x])
	extras=0
	if 'amcatnloxxx' in amcNLOname :
		for x in range(len(T.PDFNNPDFWeightsAMCNLO)):
			_allweights.append(T.PDFNNPDFWeightsAMCNLO[x]/T.PDFNNPDFWeightsAMCNLO[0])
		#extras = 101-len(T.PDFNNPDFWeightsAMCNLO)
	else:
		for x in range(len(T.LHEPdfWeight)):
		        #if(T.PDFNNPDFWeights[x]>-10 and T.PDFNNPDFWeights[x]<10): _allweights.append(T.PDFNNPDFWeights[x])
			_allweights.append(T.LHEPdfWeight[x])
		#extras = 101-len(T.LHEPdfWeight)
	#for x in range(extras):
	#	_allweights.append(1.0)
	return _allweights


def MuonsFromLQ(T):
	# Purpose: Testing. Get the muons from LQ decays and find the matching reco muons.
	#         Return TLorentzVectors of the gen and reco muons, and the indices for
	#         the recomuons as well.
	muons = []
	genmuons=[]
	recomuoninds = []
	for n in range(T.nMuon):
		m = TLorentzVector()
                m.SetPtEtaPhiM(T.Muon_pt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
		muons.append(m)

	if isData==False:
		for n in range(T.nGenPart):
			pdg = T.GenPart_pdgId[n]
			if pdg not in [13,-13]:
				continue
			motherIndex = T.GenPart_genPartIdxMother[n]

			motherid = 0
			if motherIndex>-1:
				motherid = T.GenPart_pdgId[motherIndex]
				#print 'pdgId:',pdg,'index:',T.GenParticleMotherIndex[n],'mother pdgId:',T.GenParticlePdgId[motherIndex]
			if motherid not in [42,-42]:
				continue
			m = TLorentzVector()
			m.SetPtEtaPhiM(T.GenPart_pt[n],T.GenPart_eta[n],T.GenPart_phi[n],T.GenPart_mass[n])
			genmuons.append(m)

	matchedrecomuons=[]
	emptyvector = TLorentzVector()
	emptyvector.SetPtEtaPhiM(0,0,0,0)
	#print 'number of genmuons:',len(genmuons)
	for g in genmuons:
		bestrecomuonind=-1
		mindr = 99999
		ind=-1
		for m in muons:
			ind+=1
			dr = abs(m.DeltaR(g))
			if dr<mindr:
				mindr =dr
				bestrecomuonind=ind
		if mindr<0.4:
			matchedrecomuons.append(muons[bestrecomuonind])
			recomuoninds.append(bestrecomuonind)
		else:
			matchedrecomuons.append(emptyvector)
			recomuoninds.append(-99)
		#print mindr, muons[bestrecomuonind].Pt(), g.Pt()
	while len(recomuoninds)<2 :
		recomuoninds.append(-99)
	return([genmuons,matchedrecomuons,recomuoninds])
	#return(recomuoninds)

def JetsFromLQ(T):
	# Purpose: Testing. Get the quarks from LQ decays and find the matching reco pfJets.
	#         Return TLorentzVectors of the gen and reco jets, and the indices for
	#         the recojets as well.
	jets = []
	genjets=[]
	recojetinds = []
	for n in range(T.nJet):
		if  ((T.Jet_jetId[n] & 0x2) > 0) and T.Jet_pt[n]>30 and abs(T.Jet_eta[n])<2.4 : #morse only use jets that pass tightid, fixme check jet eta
			m = TLorentzVector()
			m.SetPtEtaPhiM(T.Jet_pt[n],T.Jet_eta[n],T.Jet_phi[n],T.Jet_mass[n])
			jets.append(m)

	if isData==False:
		for n in range(T.nGenPart):
			pdg = T.GenPart_pdgId[n]
			if pdg not in [4,-4]: #Get charm quarks
				continue
			motherIndex = T.GenPart_genPartIdxMother[n]
			motherid = 0
			if motherIndex>-1:
				motherid = T.GenPart_genPartIdxMother[motherIndex]
			if motherid not in [42,-42]:
				continue
			m = TLorentzVector()
			m.SetPtEtaPhiM(T.GenPart_pt[n],T.GenPart_eta[n],T.GenPart_phi[n],T.GenPart_mass[n])
			genjets.append(m)

	matchedrecojets=[]
	emptyvector = TLorentzVector()
	emptyvector.SetPtEtaPhiM(0,0,0,0)
	for g in genjets:
		bestrecojetind=-1
		mindr = 99999
		ind=-1
		for m in jets:
			ind+=1
			dr = abs(m.DeltaR(g))
			if dr<mindr:
				mindr =dr
				bestrecojetind=ind
		if mindr<0.6:
			matchedrecojets.append(jets[bestrecojetind])
			recojetinds.append(bestrecojetind)
		else:
			matchedrecojets.append(emptyvector)
			recojetinds.append(-99)
		#print mindr, jets[bestrecojetind].Pt(), g.Pt()
	while len(recojetinds)<2 :
		recojetinds.append(-99)
	return([genjets,matchedrecojets,recojetinds])
	#return(recojetinds)

def getLeptonEventFlavorGEN(T):

	isEleEvent,isMuEvent,isTauEvent=False,False,False
	#get Zs from H, figure out lepton flavor e,mu,tau at gen level
	#gotIt=False

	if isData==False:
		for n in range(T.nGenPart):
			#if gotIt==True: continue
			pdg = T.GenPart_pdgId[n]
			#if pdg in [-15,-13,-11,11,13,15]:
			#	print n,T.GenParticlePdgId[n],T.GenParticleStatus[n],T.GenParticleMass[n],T.GenParticlePdgId[T.GenParticleMotherIndex[n]],T.GenParticleNumDaught[n],bool(T.GenParticleIsLastCopy[n])
			motherIndex = T.GenPart_genPartIdxMother[n]

			if motherIndex >= 0:
				motherid = T.GenPart_pdgId[motherIndex]
			#if motherid in [-15,15]:
			#	print n,T.GenParticlePdgId[n],T.GenParticleStatus[n],T.GenParticleMass[n],T.GenParticlePdgId[T.GenParticleMotherIndex[n]],T.GenParticleNumDaught[n],bool(T.GenParticleIsLastCopy[n])

			if pdg not in [-15,-13,-11,11,13,15]:
				continue
			if motherid in [23]:
			#if motherid in [-23,23]:
			#	grandmotherid = 0
			#       grandmotherIndex = T.GenParticleMotherIndex[motherIndex]
			#	if grandmotherIndex>-1:
			#       grandmotherid = T.GenParticlePdgId[motherIndex]
			#		print pdg,motherid,grandmotherid
			#	if grandmotherid not in [-25,25]: continue
			#print n,T.GenParticlePdgId[n],T.GenParticleStatus[n],T.GenParticleMass[n],T.GenParticlePdgId[T.GenParticleMotherIndex[n]],grandmotherid,T.GenParticleNumDaught[n],bool(T.GenParticleIsLastCopy[n])
				if pdg in [-11,11]:
					isEleEvent=True
					return [isEleEvent,isMuEvent,isTauEvent]
				if pdg in [-13,13]:
					isMuEvent=True
					return [isEleEvent,isMuEvent,isTauEvent]
				if pdg in [-15,15]:
					isTauEvent=True
					return [isEleEvent,isMuEvent,isTauEvent]
				#if (isEleEvent or isMuEvent or isTauEvent) : gotIt=True
	return [isEleEvent,isMuEvent,isTauEvent]

def LeptonsAndJetsFromHH(T,radius,isdata):
	# Purpose: Testing. HH. Get the muons from Z decays (on and off shell) and find the matching reco muons.
	#         Return TLorentzVectors of the gen and reco muons, and the indices for
	#         the recomuons as well.

	if radius == 4:
		PFJetPt = T.Jet_pt
		PFJetEta = T.Jet_eta
		PFJetPhi = T.Jet_phi
		PFJetMass = T.Jet_mass
		PFJetPartonFlavour = -1
		if isData==False:
			PFJetPartonFlavour = T.Jet_partonFlavour
		PFJetCombinedInclusiveSecondaryVertexBTag = T.Jet_btagCSVV2
	elif radius == 8:
		PFJetPt = T.FatJet_pt
		PFJetEta = T.FatJet_eta
		PFJetPhi = T.FatJet_phi
		PFJetMass = T.FatJet_mass
	# do I need this for AK8	PFJetPartonFlavour = T.PFJetPartonFlavourAK8CHS
		PFJetCombinedInclusiveSecondaryVertexBTag = T.FatJet_btagCSVV2
		SubJetPt = T.SubJet_pt
		SubJetEta = T.SubJet_eta
		SubJetPhi = T.SubJet_phi
		SubJetMass = T.SubJet_mass
		SubJetInd1 = T.FatJet_subJetIdx1
		SubJetInd2 = T.FatJet_subJetIdx2
	else:
		print 'Invalid argument: radius must be 4 or 8. Exiting.'
		sys.exit()

	muons = []
	genmuons=[]
	recomuoninds = []
	electrons = []
	genelectrons=[]
	recoelectroninds = []
	onShellZMu=False
	onShellZEle=False
	matchedrecomuons=[]
	matchedrecoelectrons=[]
	emptyvector = TLorentzVector()
	emptyvector.SetPtEtaPhiM(0,0,0,0)

###################### genMatching Muons ##########################
	for n in range(len(T.Muon_pt)):
		m = TLorentzVector()
		m.SetPtEtaPhiM(T.Muon_pt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
		muons.append(m)

	if isdata==False:
		for n in range(T.nGenPart):
			pdg = T.GenPart_pdgId[n]
			if pdg not in [13,-13]:
				continue
			motherIndex = T.GenPart_genPartIdxMother[n]

			motherid = 0
			if motherIndex>-1:
				motherid = T.GenPart_pdgId[motherIndex]
			if motherid not in [23,-23,25,-25]:
				continue
			if motherid in [23,-23]: onShellZMu=True

			# AH: here we keep also gmuon status 23 and status 1, of which mother 25. But we do not keep muon status 1 of which mother is 13, -13
			m = TLorentzVector()
			m.SetPtEtaPhiM(T.GenPart_pt[n],T.GenPart_eta[n],T.GenPart_phi[n],T.GenPart_mass[n])
			genmuons.append(m)

	for g in genmuons:
		bestrecomuonind=-1
		mindr = 99999
		ind=-1
		for m in muons:
			ind+=1
			dr = abs(m.DeltaR(g))
			if dr<mindr:
				mindr =dr
				bestrecomuonind=ind
		if mindr<0.4:
			matchedrecomuons.append(muons[bestrecomuonind])
			recomuoninds.append(bestrecomuonind)
		else:
			matchedrecomuons.append(emptyvector)
			recomuoninds.append(-99)
	while len(recomuoninds)<2 :
		recomuoninds.append(-99)

###################### genMatching Electrons ##########################
	for n in range(T.nElectron):
		m = TLorentzVector()
		m.SetPtEtaPhiM(T.Electron_pt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
		electrons.append(m)

	if isdata==False:
		for n in range(T.nGenPart):
			pdg = T.GenPart_pdgId[n]
			if pdg not in [11,-11]:
				continue
			motherIndex = T.GenPart_genPartIdxMother[n]

			motherid = 0
			if motherIndex>-1:
				motherid = T.GenPart_pdgId[motherIndex]
			if motherid not in [23,-23,25,-25]:
				continue
			if motherid in [23,-23]: onShellZEle=True
			m = TLorentzVector()
			m.SetPtEtaPhiM(T.GenPart_pt[n],T.GenPart_eta[n],T.GenPart_phi[n],T.GenPart_mass[n])
			genelectrons.append(m)

	for g in genelectrons:
		bestrecoelectronind=-1
		mindr = 99999
		ind=-1
		for m in electrons:
			ind+=1
			dr = abs(m.DeltaR(g))
			if dr<mindr:
				mindr =dr
				bestrecoelectronind=ind
		if mindr<0.4:
			matchedrecoelectrons.append(electrons[bestrecoelectronind])
			recoelectroninds.append(bestrecoelectronind)
		else:
			matchedrecoelectrons.append(emptyvector)
			recoelectroninds.append(-99)
	while len(recoelectroninds)<2 :
		recoelectroninds.append(-99)
	# Purpose: Testing. HH. Get the quarks from H and Z decays (on and off shell) and find the matching reco pfJets.
	#         Return TLorentzVectors of the gen and reco jets, and the indices for
	#         the recojets as well.
	jetsZ = []
	genjetsZ=[]
	recojetindsZ = []
	recojetOriIndsZ = []
	jetsH = []
	genjetsH=[]
	recojetindsH = []
	recojetOriIndsH = []
	genjetsZH = []

	daughterJets = [1,2,3,4,5,-5,-4,-3,-2,-1] #Get all quark flavors

	for n in range(len(PFJetPt)):
		if True :
			m = TLorentzVector()
			if radius == 4:
				m.SetPtEtaPhiM(PFJetPt[n],PFJetEta[n],PFJetPhi[n],PFJetMass[n])
			elif radius == 8:
				m.SetPtEtaPhiM(PFJetPt[n],PFJetEta[n],PFJetPhi[n],PFJetMass[n])
			jetsZ.append(m)
			jetsH.append(m)
			recojetOriIndsZ.append(n) #######These are the original Reco Jets. original index because the h jets and z jets go through second selection?
			recojetOriIndsH.append(n)

	if isdata==False:
		for n in range(T.nGenPart):
			pdg = T.GenPart_pdgId[n]
			if pdg not in daughterJets:
				continue
			motherIndex = T.GenPart_genPartIdxMother[n]
			motherid = 0
			if motherIndex>-1:
				motherid = T.GenPart_pdgId[motherIndex]
				motherStatus = T.GenPart_status[motherIndex]
				# grandMotherid = T.GenPart_pdgId[T.GenPart_genPartIdxMother[motherIndex]]

			if motherid not in [23,-23,25,-25] :#parentParticles:
				continue
			m = TLorentzVector()
			m.SetPtEtaPhiM(T.GenPart_pt[n],T.GenPart_eta[n],T.GenPart_phi[n],T.GenPart_mass[n])
			if not (onShellZMu or onShellZEle) :
				if motherid in [23,-23] : genjetsZ.append(m)
				if motherid in [25,-25] : genjetsH.append(m)
			if onShellZMu or onShellZEle :
				genjetsZH.append(m)

	if onShellZMu or onShellZEle or len(genjetsH)>=4:
		genjetsZnew,genjetsHnew = [],[]

		if len(genjetsZH)>=4:
			mass1 = abs(125.-(genjetsZH[0]+genjetsZH[1]).M())
			mass2 = abs(125.-(genjetsZH[0]+genjetsZH[2]).M())
			mass3 = abs(125.-(genjetsZH[0]+genjetsZH[3]).M())
			mass4 = abs(125.-(genjetsZH[1]+genjetsZH[2]).M())
			mass5 = abs(125.-(genjetsZH[1]+genjetsZH[3]).M())
			mass6 = abs(125.-(genjetsZH[2]+genjetsZH[3]).M())
			minMass = min(mass1,mass2,mass3,mass4,mass5,mass6)
			if mass1 == minMass: [h1,h2,z1,z2]=[0,1,2,3]
			if mass2 == minMass: [h1,h2,z1,z2]=[0,2,1,3]
			if mass3 == minMass: [h1,h2,z1,z2]=[0,3,1,2]
			if mass4 == minMass: [h1,h2,z1,z2]=[1,2,0,3]
			if mass5 == minMass: [h1,h2,z1,z2]=[1,3,0,2]
			if mass6 == minMass: [h1,h2,z1,z2]=[2,3,0,1]
			genjetsHnew.append(genjetsZH[h1])
			genjetsHnew.append(genjetsZH[h2])
			genjetsZnew.append(genjetsZH[z1])
			genjetsZnew.append(genjetsZH[z2])
		elif len(genjetsH)>=4:
			genjetsZH=genjetsH
			mass1 = abs(125.-(genjetsZH[0]+genjetsZH[1]).M())
			mass2 = abs(125.-(genjetsZH[0]+genjetsZH[2]).M())
			mass3 = abs(125.-(genjetsZH[0]+genjetsZH[3]).M())
			mass4 = abs(125.-(genjetsZH[1]+genjetsZH[2]).M())
			mass5 = abs(125.-(genjetsZH[1]+genjetsZH[3]).M())
			mass6 = abs(125.-(genjetsZH[2]+genjetsZH[3]).M())
			minMass = min(mass1,mass2,mass3,mass4,mass5,mass6)
			if mass1 == minMass: [h1,h2,z1,z2]=[0,1,2,3]
			if mass2 == minMass: [h1,h2,z1,z2]=[0,2,1,3]
			if mass3 == minMass: [h1,h2,z1,z2]=[0,3,1,2]
			if mass4 == minMass: [h1,h2,z1,z2]=[1,2,0,3]
			if mass5 == minMass: [h1,h2,z1,z2]=[1,3,0,2]
			if mass6 == minMass: [h1,h2,z1,z2]=[2,3,0,1]
			genjetsHnew.append(genjetsZH[h1])
			genjetsHnew.append(genjetsZH[h2])
			genjetsZnew.append(genjetsZH[z1])
			genjetsZnew.append(genjetsZH[z2])

		genjetsZ,genjetsH = genjetsZnew,genjetsHnew

	matchedrecojetZ=[]
	matchedrecojetH=[]
	matchedrecojetsZ=[]
	matchedrecojetsH=[]
	matchedrecosubjetsZ=[]
	matchedrecosubjetsH=[]
	#if not (onShellZMu or onShellZEle) :
	if True :
###################### AK4 JETS #####################################################
		if radius == 4:
###################### AK4 matching with 2 GEN GETS from HIGGS ######################
			usedHjetsInd = []
			for g in genjetsH:
			      	bestrecojetind=-1
				mindr = 99999
				ind=-1
				for m in jetsH:
					ind+=1
					if abs(PFJetPartonFlavour[recojetOriIndsH[ind]]) != 5 : continue
					skip = False
					for indc in range(len(usedHjetsInd)):
						if ind == usedHjetsInd[indc]:
							skip = True
							continue
					if skip: continue
					dr = abs(m.DeltaR(g))
					if dr<mindr:
						mindr =dr
						bestrecojetind=ind
				if mindr<0.4:
					matchedrecojetsH.append(jetsH[bestrecojetind])
					recojetindsH.append(recojetOriIndsH[bestrecojetind])
					usedHjetsInd.append(bestrecojetind)
				else:
					matchedrecojetsH.append(emptyvector)
					recojetindsH.append(-99)
			while len(recojetindsH)<2 :
				recojetindsH.append(-99)

###################### AK4 matching with 2 GEN GETS from Z ##########################
			usedZjetsInd = []
			for g in genjetsZ:
				bestrecojetind=-1
				mindr = 99999
				ind=-1
				for m in jetsZ:
					ind+=1
					skip = False
					for indc in range(len(usedZjetsInd)):
						if ind == usedZjetsInd[indc]:
							skip = True
							continue
					for indc in range(len(usedHjetsInd)):
						if ind == usedHjetsInd[indc]:
							skip = True
							continue
					if skip: continue
					dr = abs(m.DeltaR(g))
					if dr<mindr:
						mindr =dr
						bestrecojetind=ind
				if mindr<0.4:
					matchedrecojetsZ.append(jetsZ[bestrecojetind])
					recojetindsZ.append(recojetOriIndsZ[bestrecojetind])
					usedZjetsInd.append(bestrecojetind)
				#recojetindsZ.append(bestrecojetind)
				else:
					matchedrecojetsZ.append(emptyvector)
					recojetindsZ.append(-99)
			while len(recojetindsZ)<2 :
				recojetindsZ.append(-99)

###################### AK8 JETS #####################################################
		elif radius == 8:
###################### AK8 matching with 2 GEN GETS from HIGGS ######################
			usedHjetsInd = []
			mindr1 = 99999
			mindr2 = 99999
			bestrecojetind=-1
			bestindices = [-1,-1]

			for j in range(len(jetsH)):

				skip = False
				for indc in range(len(usedHjetsInd)):
					if j == usedHjetsInd[indc]:
						skip = True
						continue
				if skip: continue

				subjet1,subjet2 = [],[]

				if SubJetInd1[j] == -1:
					sub1 = emptyvector
				else:
					sub1 = TLorentzVector()
					sub1.SetPtEtaPhiM(SubJetPt[SubJetInd1[j]],SubJetEta[SubJetInd1[j]],SubJetPhi[SubJetInd1[j]],SubJetMass[SubJetInd1[j]])

				if SubJetInd2[j] == -1:
					sub2 = emptyvector
				else:
					sub2 = TLorentzVector()
					sub2.SetPtEtaPhiM(SubJetPt[SubJetInd2[j]],SubJetEta[SubJetInd2[j]],SubJetPhi[SubJetInd2[j]],SubJetMass[SubJetInd2[j]])

				subjet1.append(sub1)
				subjet2.append(sub2)

				mindr = 99999

				for g in range(len(genjetsH)):

					genjet = genjetsH[g]

					dr1 = sub1.DeltaR(genjet) if sub1 else 99999
					dr2 = sub2.DeltaR(genjet) if sub2 else 99999

					mindrtotal = dr1 + dr2

					if mindrtotal < mindr:
						mindr1 = dr1
						mindr2 = dr2
						mindr = mindrtotal
						bestindices = [j, g]

			bestrecojetind = bestindices[0]

			CSV_jetH = 0

			if mindr1<0.6 and mindr2<0.6:
				matchedrecojetH.append(jetsH[bestrecojetind])
				recojetindsH.append(recojetOriIndsH[bestrecojetind])
				usedHjetsInd.append(bestrecojetind)
				CSV_jetH = PFJetCombinedInclusiveSecondaryVertexBTag[bestrecojetind]
			else:
				matchedrecojetH.append(emptyvector)
				recojetindsH.append(-99)

			while len(recojetindsH)<1 :
				recojetindsH.append(-99)

###################### AK8 matching with 2 GEN GETS from Z ######################
			usedZjetsInd = []
			mindr1 = 99999
			mindr2 = 99999
			bestrecojetind=-1

			for j in range(len(jetsZ)):

				skip = False
				for indc in range(len(usedHjetsInd)):
					if j == usedHjetsInd[indc]:
						skip = True
						continue
				for indc in range(len(usedZjetsInd)):
					if j == usedZjetsInd[indc]:
						skip = True
						continue
				if skip: continue

				subjet1,subjet2 = [],[]

				if SubJetInd1[j] == -1:
					sub1 = emptyvector
				else:
					sub1 = TLorentzVector()
					sub1.SetPtEtaPhiM(SubJetPt[SubJetInd1[j]],SubJetEta[SubJetInd1[j]],SubJetPhi[SubJetInd1[j]],SubJetMass[SubJetInd1[j]])

				if SubJetInd2[j] == -1:
					sub2 = emptyvector
				else:
					sub2 = TLorentzVector()
					sub2.SetPtEtaPhiM(SubJetPt[SubJetInd2[j]],SubJetEta[SubJetInd2[j]],SubJetPhi[SubJetInd2[j]],SubJetMass[SubJetInd2[j]])

				subjet1.append(sub1)
				subjet2.append(sub2)

				mindr = 99999
				for g in range(len(genjetsZ)):

					genjet = genjetsZ[g]

					dr1 = sub1.DeltaR(genjet) if sub1 else 99999
					dr2 = sub2.DeltaR(genjet) if sub2 else 99999

					mindrtotal = dr1 + dr2

					if mindrtotal < mindr:
						mindr1 = dr1
						mindr2 = dr2
						mindr = mindrtotal
						bestindices = [j, g]

			bestrecojetind = bestindices[0]

			CSV_jetZ = 0

			if mindr1<0.6 and mindr2<0.6:
				matchedrecojetZ.append(jetsZ[bestrecojetind])
				recojetindsZ.append(recojetOriIndsZ[bestrecojetind])
				usedZjetsInd.append(bestrecojetind)
				CSV_jetZ = PFJetCombinedInclusiveSecondaryVertexBTag[bestrecojetind]
			else:
				matchedrecojetZ.append(emptyvector)
				recojetindsZ.append(-99)

			while len(recojetindsZ)<1 :
				recojetindsZ.append(-99)

###################### Append vectors with 0 if less than 2 elements ######################
	while len(genmuons)<2:
		genmuons.append(emptyvector)
	while len(genelectrons)<2:
		genelectrons.append(emptyvector)
	while len(matchedrecomuons)<2:
		matchedrecomuons.append(emptyvector)
	while len(matchedrecoelectrons)<2:
		matchedrecoelectrons.append(emptyvector)

	if radius == 4:
		while len(genjetsH)<2:
			genjetsH.append(emptyvector)
		while len(genjetsZ)<2:
			genjetsZ.append(emptyvector)
		while len(matchedrecojetsH)<2:
			matchedrecojetsH.append(emptyvector)
		while len(matchedrecojetsZ)<2:
			matchedrecojetsZ.append(emptyvector)

	elif radius == 8:
		while len(jetsH)<1:
			jetsH.append(emptyvector)
		while len(genjetsH)<2:
			genjetsH.append(emptyvector)
		while len(genjetsZ)<2:
			genjetsZ.append(emptyvector)
		while len(matchedrecojetH)<1:
			matchedrecojetH.append(emptyvector)
		while len(matchedrecojetZ)<1:
			matchedrecojetZ.append(emptyvector)
		while len(matchedrecojetsZ)<2:
			matchedrecojetsZ.append(emptyvector)

		dRujH=0
		dRujZ=0
		gendRujH=0
		gendRujZ=0
		combinedmuons = matchedrecomuons[0]+matchedrecomuons[1]

		for j in matchedrecojetH:
			dRujH=j.DeltaR(combinedmuons)

		for j in matchedrecojetZ:
			dRujZ=j.DeltaR(combinedmuons)

######################## dR highest pt gen jet and highest pt gen muon ########################
		if genmuons[0].Pt() >= genmuons[1].Pt():
			highestptGenMuon = genmuons[0]
		else:
			highestptGenMuon = genmuons[1]

		if genjetsH[0].Pt() >= genjetsH[1].Pt():
			highestptGenJetH = genjetsH[0]
		else:
			highestptGenJetH = genjetsH[1]

		if genjetsZ[0].Pt() >= genjetsZ[1].Pt():
			highestptGenJetZ = genjetsZ[0]
		else:
			highestptGenJetZ = genjetsZ[1]

		gendRujH=highestptGenJetH.DeltaR(highestptGenMuon)
		gendRujZ=highestptGenJetZ.DeltaR(highestptGenMuon)

	if radius == 4: return([genmuons,matchedrecomuons,recomuoninds,genelectrons,matchedrecoelectrons,recoelectroninds,genjetsH,matchedrecojetsH,recojetindsH,genjetsZ,matchedrecojetsZ,recojetindsZ,onShellZMu,onShellZEle])
	elif radius == 8: return([jetsH,matchedrecojetH,recojetindsH,matchedrecojetZ,recojetindsZ,dRujH,dRujZ,gendRujH,gendRujZ,CSV_jetH,CSV_jetZ])


def PropagatePTChangeToMET(met,original_object,varied_object):
	# Purpose: This takes an input TLorentzVector met representing the missing ET
	#         (no eta component), and an original object (arg 2), which has been
	#         kinmatically modified for a systematic (arg 3), and modifies the
	#         met to compensate for the change in the object.
	return  met + varied_object - original_object


def LooseIDMuons(T,_met,variation,isdata):
	# Purpose: Gets the collection of muons passing loose muon ID.
	#         Returns muons as TLorentzVectors, and indices corrresponding
	#         to the surviving muons of the muon collection.
	#         Also returns modified MET for systematic variations.
	muons = []
	muoninds = []
	if variation=='MESup':
		#_MuonPt = [(pt + pt*(0.05*pt/1000.0)) for pt in T.MuonPt]#original
		_MuonPt = [(pt + pt*(0.10*pt/1000.0)) for pt in T.Muon_pt]#updated to Zprime 13TeV study number
	elif variation=='MESdown':
		#_MuonPt = [(pt - pt*(0.05*pt/1000.0)) for pt in T.MuonPt]
		_MuonPt = [(pt - pt*(0.10*pt/1000.0)) for pt in T.Muon_pt]
	elif variation=='MER':
		_MuonPt = [pt+pt*tRand.Gaus(0.0,  0.01*(pt<=200.0) + (0.04)*(pt>200.0) ) for pt in T.Muon_pt]
	else:
		_MuonPt = [pt for pt in T.Muon_pt]

	if (isdata):
		_MuonPt = [pt for pt in T.Muon_pt]

	trk_isos = []
	charges = []
	deltainvpts = []

	nequiv = []
	for n in range(len(T.Muon_pt)):
		#if T.MuonIsGlobal[n]: #not necessary anymore - global muon requirement encompassed later
		nequiv.append(n)

	# Loop over muons using the pT array from above
	for n in range(len(_MuonPt)):

		# Some muon alignment studies use the inverse diff of the high pT and Trk pT values
		deltainvpt = -1.0
		if ( T.Muon_ptTuneP[nequiv[n]] > 0.0 ) and (_MuonPt[n]>0.0):
			deltainvpt = ( 1.0/T.Muon_ptTuneP[nequiv[n]] - 1.0/_MuonPt[n])

		# For alignment correction studies in MC, the pT is modified according to
		# parameterizations of the position
		if alignementcorrswitch == True and isdata==False:
			if abs(deltainvpt) > 0.0000001:
				__Pt_mu = _MuonPt[n]
				__Eta_mu = T.Muon_eta[n]
				__Phi_mu = T.Muon_phi[n]
				__Charge_mu = T.Muon_charge[nequiv[n]]
				if (__Pt_mu >200)*(abs(__Eta_mu) < 0.9)      :
					_MuonPt[n] =  ( (1.0) / ( -5e-05*__Charge_mu*sin(-1.4514813+__Phi_mu ) + 1.0/__Pt_mu ) )
				deltainvpt = ( 1.0/T.Muon_ptTuneP[nequiv[n]] - 1.0/_MuonPt[n])


		# For the ID, begin by assuming it passes. Veto if it fails any condition
		# conditions from https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideMuonIdRun2#Short_Term_Medium_Muon_Definitio
                # https://twiki.cern.ch/twiki/bin/view/CMS/SWGuideMuonIdRun2?rev=31#Short_Term_Instructions_for_Mori
		# NTuple definitions in https://raw.githubusercontent.com/CMSLQ/RootTupleMakerV2/master/src/RootTupleMakerV2_Muons.cc
		Pass = True

                # Require Loose muon flag
	        Pass *= T.Muon_looseId[n] > 0

	        #fixme these two are equivalent to IsLooseMuon #?
		#Pass *= T.MuonIsPF[n]
	        #Pass *= (T.MuonIsGlobal[n] or T.MuonIsTracker[n])

		# A preliminary pT cut.
		Pass *= (_MuonPt[n] > 8)#fixme offline cuts are 20(10)

		# Eta requirement
	        Pass *= abs(T.Muon_eta[n])<2.4

		# Isolation condition using combined PF relative isolation - 0.25 for loose (98% efficiency), 0.15 for tight (95% efficiency)
	        correctedIso = T.Muon_pfRelIso04_all[n]
		# Don't apply isolation for QCD studies
		if nonisoswitch != True:
			Pass *= correctedIso < 0.25

		# Propagate MET changes if undergoing systematic variation
		if (Pass):
			NewMu = TLorentzVector()
			OldMu = TLorentzVector()
			NewMu.SetPtEtaPhiM(_MuonPt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
			#NewMu.SetPtEtaPhiM(_MuonPt[n],T.MuonEta[n],T.MuonPhi[n],0)
			OldMu.SetPtEtaPhiM(T.Muon_pt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
			#OldMu.SetPtEtaPhiM(T.MuonPt[n],T.MuonEta[n],T.MuonPhi[n],0)
			_met = PropagatePTChangeToMET(_met,OldMu,NewMu)

			# Append items to retun if the muon is good

			muons.append(NewMu)
			muoninds.append(n)
			pfid.append(T.Muon_isPFcand[nequiv[n]])
			charges.append(T.Muon_charge[n])
			layers.append(T.Muon_nTrackerLayers[nequiv[n]])
			trk_isos.append(correctedIso)
			deltainvpts.append(deltainvpt)

	return [muons,muoninds,_met,trk_isos,charges,deltainvpts,pfid,layers]


def MediumIDMuons(T,_met,variation,isdata):
	# Purpose: Gets the collection of muons passing medium muon ID.
	#         Returns muons as TLorentzVectors, and indices corrresponding
	#         to the surviving muons of the muon collection.
	#         Also returns modified MET for systematic variations.
	muons = []
	muoninds = []
	if variation=='MESup':
		#_MuonPt = [(pt + pt*(0.05*pt/1000.0)) for pt in T.MuonPt]#original
		_MuonPt = [(pt + pt*(0.10*pt/1000.0)) for pt in T.Muon_pt]#updated to Zprime 13TeV study number
	elif variation=='MESdown':
		#_MuonPt = [(pt - pt*(0.05*pt/1000.0)) for pt in T.MuonPt]
		_MuonPt = [(pt - pt*(0.10*pt/1000.0)) for pt in T.Muon_pt]
	elif variation=='MER':
		_MuonPt = [pt+pt*tRand.Gaus(0.0,  0.01*(pt<=200.0) + (0.04)*(pt>200.0) ) for pt in T.Muon_pt]
	else:
		_MuonPt = [pt for pt in T.Muon_pt]

	if (isdata):
		_MuonPt = [pt for pt in T.Muon_pt]

	trk_isos = []
	charges = []
	deltainvpts = []

	pfid = []
	layers = []
	nequiv = []

	for n in range(len(T.Muon_pt)):
		nequiv.append(n)

	# Loop over muons using the pT array from above
	for n in range(len(_MuonPt)):

		# Some muon alignment studies use the inverse diff of the high pT and Trk pT values
		deltainvpt = -1.0
		if ( T.Muon_ptTuneP[nequiv[n]] > 0.0 ) and (_MuonPt[n]>0.0):
			deltainvpt = ( 1.0/T.Muon_ptTuneP[nequiv[n]] - 1.0/_MuonPt[n])

		# For alignment correction studies in MC, the pT is modified according to
		# parameterizations of the position
		if alignementcorrswitch == True and isdata==False:
			if abs(deltainvpt) > 0.0000001:
				__Pt_mu = _MuonPt[n]
				__Eta_mu = T.Muon_eta[n]
				__Phi_mu = T.Muon_phi[n]
				__Charge_mu = T.Muon_charge[nequiv[n]]
				if (__Pt_mu >200)*(abs(__Eta_mu) < 0.9)      :
					_MuonPt[n] =  ( (1.0) / ( -5e-05*__Charge_mu*sin(-1.4514813+__Phi_mu ) + 1.0/__Pt_mu ) )
				deltainvpt = ( 1.0/T.Muon_ptTuneP[nequiv[n]] - 1.0/_MuonPt[n])


		# For the ID, begin by assuming it passes. Veto if it fails any condition
		# Conditions from https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideMuonIdRun2
		# NTuple definitions in https://raw.githubusercontent.com/CMSLQ/RootTupleMakerV2/master/src/RootTupleMakerV2_Muons.cc

		Pass = True
		# A preliminary pT cut.
		Pass *= (_MuonPt[n] > 10)#fixme offline cuts are 20(10)

		# Eta requirement
		Pass *= abs(T.Muon_eta[n])<2.4

                # Require Loose muon flag
	        Pass *= T.Muon_mediumId[n] > 0 #? does this need to be loose and do we need valid fraction of hits

		# Isolation condition using combined PF relative isolation - 0.25 for loose (98% efficiency), 0.15 for tight (95% efficiency)
	        correctedIso = T.Muon_pfRelIso04_all[n]

		# Don't apply isolation for QCD studies
		if nonisoswitch != True:
			Pass *= correctedIso < 0.25

		# Prompt requirement
		Pass *= abs(T.Muon_dxy[n]) < 0.2
		Pass *= abs(T.Muon_dz[n])  < 0.5

		# Propagate MET changes if undergoing systematic variation
		if (Pass):
			NewMu = TLorentzVector()
			OldMu = TLorentzVector()
			NewMu.SetPtEtaPhiM(_MuonPt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
			OldMu.SetPtEtaPhiM(T.Muon_pt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
			_met = PropagatePTChangeToMET(_met,OldMu,NewMu)

			# Append items to retun if the muon is good

			muons.append(NewMu)
			muoninds.append(n)
			pfid.append(T.Muon_isPFcand[nequiv[n]])
			charges.append(T.Muon_charge[n])
			trk_isos.append(correctedIso)
			layers.append(T.Muon_nTrackerLayers[nequiv[n]])
			deltainvpts.append(deltainvpt)
	return [muons,muoninds,_met,trk_isos,charges,deltainvpts,pfid,layers]

def mvaWP90Electrons(T,_met,variation,isdata):
	# Purpose: Gets the collection of electrons passing Loose Electron ID.
	#         Returns electrons as TLorentzVectors, and indices corrresponding
	#         to the surviving electrons of the electron collection.
	#         Also returns modified MET for systematic variations.
	#         https://twiki.cern.ch/twiki/bin/view/CMS/CutBasedElectronIdentificationRun2#Recommended_Working_points_for_2
	electrons = []
	electroninds = []
	if variation=='EESup':
		_ElectronPt = [pt*1.02 for pt in T.Electron_pt]
	elif variation=='EESdown':
		_ElectronPt = [pt*0.98 for pt in T.Electron_pt]
	elif variation=='EER':
		_ElectronPt = [pt+pt*tRand.Gaus(0.0,0.04) for pt in T.Electron_pt]
	else:
		_ElectronPt = [pt for pt in T.Electron_pt]

	trk_isos = []
	charges = []
	deltainvpts = []
#?	pfid = []
#?	layers = []
	_idIsoSFs=[]
	_idIsoSFsUp=[]
	_idIsoSFsDown=[]
	_hlt1SFs=[]
	_hlt1SFsUp=[]
	_hlt1SFsDown=[]
	_hlt2SFs=[]
	_hlt2SFsUp=[]
	_hlt2SFsDown=[]

	for n in range(len(_ElectronPt)):
		Pass = True
		Pass *= (T.Electron_pt[n] > 12)
		Pass *= abs(T.Electron_eta[n])<2.5

		barrel = (abs(T.Electron_eta[n]))<1.442
		endcap = (abs(T.Electron_eta[n]))>1.56
#?		barrel = (abs(T.ElectronSCEta[n]))<1.442
#?		endcap = (abs(T.ElectronSCEta[n]))>1.56
		Pass *= (barrel+endcap)

	        Pass *= T.Electron_mvaFall17V2noIso_WP90[n]>0

	        if (barrel):
			Pass *= abs(T.Electron_dxy[n])<0.05
			Pass *= abs(T.Electron_dz[n]) <0.10
		elif (endcap):
			Pass *= abs(T.Electron_dxy[n])< 0.10
			Pass *= abs(T.Electron_dz[n]) < 0.20

		iso = T.Electron_mvaFall17V1Iso[n]

		"""
	        ecal_energy_inverse = 1.0/T.ElectronEcalEnergy[n]
		eSCoverP = T.ElectronESuperClusterOverP[n]

                #HLT-safe cuts, except iso which is in nonisoswitch below
		#fixme removing hlt-safe cuts for now

        	if (barrel):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.011
	                Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.004
		        Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.020
		        Pass *= T.ElectronHoE[n]<0.060
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.013
		        #Pass *= T.ElectronNormalizedChi2[n]<
        	elif (endcap):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.031
	                #Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.004
		        #Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.020
		        Pass *= T.ElectronHoE[n]<0.065
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.013
		        Pass *= T.ElectronNormalizedChi2[n]<3.0

		#Isolation
		chad = T.ElectronPFChargedHadronIso03[n]
		nhad = T.ElectronPFNeutralHadronIso03[n]
		pho  = T.ElectronPFPhotonIso03[n]

		eA = getElectronEffectiveArea(T.Electron_eta[n])
		iso = chad + max(0.0, nhad + pho - T.ElectronRhoIsoHEEP[n]*eA)
		iso = iso/_ElectronPt[n]

		"""

		iso=T.Electron_mvaFall17V2Iso[n]/T.Electron_pt[n]
		# Don't apply isolation for QCD studies
		if nonisoswitch != True:
			if (barrel):
				#Pass *= iso<0.0588#tight
				Pass *= T.Electron_mvaFall17V2noIso_WP90[n]>0
				#Pass *= iso<0.15#ZH(bb)
		                #fixme removing hlt-safe cuts for now
		                #Pass *= ((T.ElectronEcalPFClusterIso[n] - 0.165*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.160
		                #Pass *= ((T.ElectronHcalPFClusterIso[n] - 0.060*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #Pass *= (T.ElectronTrkIsoDR03[n]/_ElectronPt[n])<0.08
			elif (endcap):
				#Pass *= iso<0.0571
				Pass *= T.Electron_mvaFall17V2noIso_WP90[n]>0
				#Pass *= iso<0.15#ZH(bb)
                                #fixme removing hlt-safe cuts for now
		                #Pass *= ((T.ElectronEcalPFClusterIso[n] - 0.132*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #Pass *= ((T.ElectronHcalPFClusterIso[n] - 0.131*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120

		[_idIsoSF,_idIsoSFUp,_idIsoSFDown,_hlt1SF,_hlt1SFup,_hlt1SFdown,_hlt2SF,_hlt2SFup,_hlt2SFdown] = getSFelectron(_ElectronPt[n],T.Electron_eta[n])
#?		[_idIsoSF,_idIsoSFUp,_idIsoSFDown,_hlt1SF,_hlt1SFup,_hlt1SFdown,_hlt2SF,_hlt2SFup,_hlt2SFdown] = getSFelectron(_ElectronPt[n],T.ElectronSCEta[n]) need SCEta above?

		if (Pass):
			NewEl = TLorentzVector()
			OldEl = TLorentzVector()
			NewEl.SetPtEtaPhiM(_ElectronPt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			OldEl.SetPtEtaPhiM(T.Electron_pt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
#?			NewEl.SetPtEtaPhiM(_ElectronPt[n],T.ElectronSCEta[n],T.Electron_phi[n],0)
#?			OldEl.SetPtEtaPhiM(T.Electron_pt[n],T.ElectronSCEta[n],T.Electron_phi[n],0)
			met = PropagatePTChangeToMET(_met,OldEl,NewEl)

		if (Pass):
			electrons.append(NewEl)
			electroninds.append(n)
			trk_isos.append(iso)
			charges.append(T.Electron_charge[n])
			deltainvpts.append(0.)
#?			pfid.append(0.)
#?			layers.append(0.)
			_idIsoSFs.append(_idIsoSF)
			_idIsoSFsUp.append(_idIsoSFUp)
			_idIsoSFsDown.append(_idIsoSFDown)
			_hlt1SFs.append(_hlt1SF)
			_hlt1SFsUp.append(_hlt1SFup)
			_hlt1SFsDown.append(_hlt1SFdown)
			_hlt2SFs.append(_hlt2SF)
			_hlt2SFsUp.append(_hlt2SFup)
			_hlt2SFsDown.append(_hlt2SFdown)

	return [electrons,electroninds,_met,trk_isos,charges,_idIsoSFs,_idIsoSFsUp,_idIsoSFsDown,_hlt1SFs,_hlt1SFsUp,_hlt1SFsDown,_hlt2SFs,_hlt2SFsUp,_hlt2SFsDown]


def LooseElectrons(T,_met,variation,isdata):
	# Purpose: Gets the collection of electrons passing Loose Electron ID.
	#         Returns electrons as TLorentzVectors, and indices corrresponding
	#         to the surviving electrons of the electron collection.
	#         Also returns modified MET for systematic variations.
	#         https://twiki.cern.ch/twiki/bin/view/CMS/CutBasedElectronIdentificationRun2#Recommended_Working_points_for_2
	electrons = []
	electroninds = []
	if variation=='EESup':
		_ElectronPt = [pt*1.01 for pt in T.Electron_pt]
	elif variation=='EESdown':
		_ElectronPt = [pt*0.99 for pt in T.Electron_pt]
	elif variation=='EER':
		_ElectronPt = [pt+pt*tRand.Gaus(0.0,0.04) for pt in T.Electron_pt]
	else:
		_ElectronPt = [pt for pt in T.Electron_pt]

	trk_isos = []
	charges = []
	deltainvpts = []
	pfid = []
	layers = []

	for n in range(len(_ElectronPt)):
		Pass = True
		Pass *= (T.Electron_pt[n] > 12)
		Pass *= abs(T.Electron_eta[n])<2.5

		barrel = bool((abs(T.Electron_eta[n]))<1.442) #?
		endcap = bool((abs(T.Electron_eta[n]))>1.56) #?
		Pass *= (barrel+endcap)

	        Pass *= T.Electron_mvaFall17V2Iso_WPL[n]>0

	        if (barrel):
			Pass *= abs(T.Electron_dxy[n])<0.05
			Pass *= abs(T.Electron_dz[n]) <0.10
		elif (endcap):
			Pass *= abs(T.Electron_dxy[n])< 0.10
			Pass *= abs(T.Electron_dz[n]) < 0.20


		""" #?
	        ecal_energy_inverse = 1.0/T.ElectronEcalEnergy[n]
		eSCoverP = T.ElectronESuperClusterOverP[n]

		#HLT-safe cuts, except iso which is in nonisoswitch below
        	if (barrel):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.011
	                Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.004
		        Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.020
		        Pass *= T.ElectronHoE[n]<0.060
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.013
		        #Pass *= T.ElectronNormalizedChi2[n]<
        	elif (endcap):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.031
	                #Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.004
		        #Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.020
		        Pass *= T.ElectronHoE[n]<0.065
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.013
		        Pass *= T.ElectronNormalizedChi2[n]<3.0

		#Isolation
		chad = T.ElectronPFChargedHadronIso03[n]
		nhad = T.ElectronPFNeutralHadronIso03[n]
		pho  = T.ElectronPFPhotonIso03[n]

		eA = getElectronEffectiveArea(T.ElectronEta[n])
		iso = chad + max(0.0, nhad + pho - T.ElectronRhoIsoHEEP[n]*eA)
		iso = iso/_ElectronPt[n]

		"""
		iso = T.Electron_mvaFall17V2Iso[n]/T.Electron_pt[n]
		# Don't apply isolation for QCD studies
		if nonisoswitch != True:
			if (barrel):
				Pass *= iso<0.0588
		                #? Pass *= ((T.ElectronEcalPFClusterIso[n] - 0.165*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.160
		                #? Pass *= ((T.ElectronHcalPFClusterIso[n] - 0.060*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #? Pass *= (T.ElectronTrkIsoDR03[n]/_ElectronPt[n])<0.08
			elif (endcap):
				Pass *= iso<0.0571
		                #? Pass *= ((T.ElectronEcalPFClusterIso[n] - 0.132*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #? Pass *= ((T.ElectronHcalPFClusterIso[n] - 0.131*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #? Pass *= (T.ElectronTrkIsoDR03[n]/_ElectronPt[n])<0.08

		if (Pass):
			NewEl = TLorentzVector()
			OldEl = TLorentzVector()
			NewEl.SetPtEtaPhiM(_ElectronPt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			OldEl.SetPtEtaPhiM(T.Electron_pt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			met = PropagatePTChangeToMET(_met,OldEl,NewEl)

		if (Pass):
			electrons.append(NewEl)
			electroninds.append(n)
			trk_isos.append(iso)
			charges.append(T.Electron_charge[n])
			deltainvpts.append(0.)
			pfid.append(0.)
			layers.append(0.)

	return [electrons,electroninds,_met,trk_isos,charges]


def MediumElectrons(T,_met,variation,isdata):
	# Purpose: Gets the collection of electrons passing Tight Electron ID.
	#         Returns electrons as TLorentzVectors, and indices corrresponding
	#         to the surviving electrons of the electron collection.
	#         Also returns modified MET for systematic variations.
	#         https://twiki.cern.ch/twiki/bin/view/CMS/CutBasedElectronIdentificationRun2#Recommended_Working_points_for_2
	electrons = []
	electroninds = []
	if variation=='EESup':
		_ElectronPt = [pt*1.01 for pt in T.Electron_pt]
	elif variation=='EESdown':
		_ElectronPt = [pt*0.99 for pt in T.Electron_pt]
	elif variation=='EER':
		_ElectronPt = [pt+pt*tRand.Gaus(0.0,0.04) for pt in T.Electron_pt]
	else:
		_ElectronPt = [pt for pt in T.Electron_pt]

	trk_isos = []
	charges = []
	deltainvpts = []
	pfid = []
	layers = []

	for n in range(len(_ElectronPt)):
		Pass = True
		Pass *= (_ElectronPt[n] > 15)
		Pass *= abs(T.Electron_eta[n])<2.5 #?

		barrel = bool((abs(T.Electron_eta[n]))<1.442) #?
		endcap = bool((abs(T.Electron_eta[n]))>1.56)
		Pass *= (barrel+endcap)>0

	        Pass *= T.Electron_mvaFall17V2noIso_WP90[n]>0
		"""
	        ecal_energy_inverse = 1.0/T.ElectronEcalEnergy[n]
		eSCoverP = T.ElectronESuperClusterOverP[n]

        	if (barrel):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.00998
	                Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.00311
		        Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.103
		        Pass *= T.ElectronHoE[n]<0.253
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.134
	                Pass *= T.ElectronMissingHits[n]<=1
	                Pass *= bool(T.ElectronHasMatchedConvPhot[n])==False
        	elif (endcap):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.0298
	                Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.00609
		        Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.045
		        Pass *= T.ElectronHoE[n]<0.0878
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.13
	                Pass *= T.ElectronMissingHits[n]<=1
	                Pass *= bool(T.ElectronHasMatchedConvPhot[n])==False

		#HLT-safe cuts, except iso which is in nonisoswitch below
        	if (barrel):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.011
	                Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.004
		        Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.020
		        Pass *= T.ElectronHoE[n]<0.060
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.013
		        #Pass *= T.ElectronNormalizedChi2[n]<
        	elif (endcap):
			Pass *= T.ElectronFull5x5SigmaIEtaIEta[n]<0.031
	                #Pass *= abs(T.ElectronDeltaEtaTrkSeedSC[n])<0.004
		        #Pass *= abs(T.ElectronDeltaPhiTrkSC[n])<0.020
		        Pass *= T.ElectronHoE[n]<0.065
		        Pass *= abs(1.0 - eSCoverP)*ecal_energy_inverse<0.013
		        Pass *= T.ElectronNormalizedChi2[n]<3.0

		chad = T.ElectronPFChargedHadronIso03[n]
		nhad = T.ElectronPFNeutralHadronIso03[n]
		pho  = T.ElectronPFPhotonIso03[n]

		eA = getElectronEffectiveArea(T.ElectronEta[n])
		iso = chad + max(0.0, nhad + pho - T.ElectronRhoIsoHEEP[n]*eA)
		iso = iso/_ElectronPt[n]
		"""
		iso = T.Electron_mvaFall17V2Iso[n]
		# Don't apply isolation for QCD studies
		if nonisoswitch != True:
			if (barrel):
				Pass *= iso<0.0695
		                #? Pass *= ((T.ElectronEcalPFClusterIso[n] - 0.165*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.160
		                #? Pass *= ((T.ElectronHcalPFClusterIso[n] - 0.060*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #? Pass *= (T.ElectronTrkIsoDR03[n]/_ElectronPt[n])<0.08
			elif (endcap):
				Pass *= iso<0.0821
		                #? Pass *= ((T.ElectronEcalPFClusterIso[n] - 0.132*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #? Pass *= ((T.ElectronHcalPFClusterIso[n] - 0.131*T.fixedGridRhoFastjetCentralCalo)/_ElectronPt[n])<0.120
		                #? Pass *= (T.ElectronTrkIsoDR03[n]/_ElectronPt[n])<0.08

		# impact parameter requirements
        	if (barrel):
			Pass *= abs(T.Electron_dxy[n])<0.05
			Pass *= abs(T.Electron_dz[n]) <0.10
		elif (endcap):
			Pass *= abs(T.Electron_dxy[n])< 0.10
			Pass *= abs(T.Electron_dz[n]) < 0.20

		if (Pass):
			NewEl = TLorentzVector()
			OldEl = TLorentzVector()
			NewEl.SetPtEtaPhiM(_ElectronPt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			OldEl.SetPtEtaPhiM(T.Electron_pt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			met = PropagatePTChangeToMET(_met,OldEl,NewEl)

		if (Pass):
			electrons.append(NewEl)
			electroninds.append(n)
			trk_isos.append(iso) #?
			charges.append(T.Electron_charge[n])
			deltainvpts.append(0.)
			pfid.append(0.)
			layers.append(0.)

	return [electrons,electroninds,_met,trk_isos,charges]


def TightElectrons(T,_met,variation,isdata):
	# Purpose: Gets the collection of electrons passing Tight Electron ID.
	#         Returns electrons as TLorentzVectors, and indices corrresponding
	#         to the surviving electrons of the electron collection.
	#         Also returns modified MET for systematic variations.
	#         https://twiki.cern.ch/twiki/bin/view/CMS/CutBasedElectronIdentificationRun2#Recommended_Working_points_for_2
	electrons = []
	electroninds = []
	if variation=='EESup':
		_ElectronPt = [pt*1.01 for pt in T.Electron_pt]
	elif variation=='EESdown':
		_ElectronPt = [pt*0.99 for pt in T.Electron_pt]
	elif variation=='EER':
		_ElectronPt = [pt+pt*tRand.Gaus(0.0,0.04) for pt in T.Electron_pt]
	else:
		_ElectronPt = [pt for pt in T.Electron_pt]

	trk_isos = []
	charges = []
	deltainvpts = []
	pfid = []
	layers = []

	for n in range(len(_ElectronPt)):
		Pass = True
		Pass *= (T.Electron_pt[n] > 12)
		Pass *= abs(T.Electron_eta[n])<2.5

		barrel = bool((abs(T.Electron_eta[n]))<1.442) #?
		endcap = bool((abs(T.Electron_eta[n]))>1.56) #?
		Pass *= (barrel+endcap)

	        Pass *= T.Electron_mvaFall17V2Iso_WP80[n]>0

        	if (barrel):
			Pass *= abs(T.Electron_dxy[n])<0.05
			Pass *= abs(T.Electron_dz[n]) <0.10
		elif (endcap):
			Pass *= abs(T.Electron_dxy[n])< 0.10
			Pass *= abs(T.Electron_dz[n]) < 0.20

		if (Pass):
			NewEl = TLorentzVector()
			OldEl = TLorentzVector()
			NewEl.SetPtEtaPhiM(_ElectronPt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			OldEl.SetPtEtaPhiM(T.Electron_pt[n],T.Electron_eta[n],T.Electron_phi[n],T.Electron_mass[n])
			met = PropagatePTChangeToMET(_met,OldEl,NewEl)

		if (Pass):
			electrons.append(NewEl)
			electroninds.append(n)
			trk_isos.append(T.Electron_mvaFall17V2Iso[n]) #?
			charges.append(T.Electron_charge[n])
			deltainvpts.append(0.)
			pfid.append(0.)
			layers.append(0.)

	return [electrons,electroninds,_met,trk_isos,charges]


def getSFelectron(_pt,_eta):
	SFbyPt = []
	pts = [[20.00,22.00],[22.00,25.00],[25.00,30.00],[30.00,35.00],[35.00,40.00],[40.00,50.00],[50.00,60.00],[60.00,70.00],[70.00,80.00],[80.00,100.00],[100.00,120.00],[120.00,200.00]]
	if _pt<=20.00: _pt=20.01
	if _pt>=200.00: _pt=199.99
	if _eta<=-2.50: _eta=-2.499
	if _eta>=2.50: _eta=2.499
	idIsoSFbyPt,hlt1SFbyPt,hlt2SFbyPt=1.0,1.0,1.0
	index=0
	for x in pts:
		if _pt>=x[0] and _pt<=x[1]:
			break
		index=index+1
	if _eta>-2.50 and _eta<=-2.17: idIsoSFbyPt = [[0.879, 0.039],[0.866, 0.129],[0.9, 0.054],[0.933, 0.022],[0.944, 0.018],[0.963, 0.017],[0.967, 0.044],[0.981, 0.033],[1.0, 0.091],[1.02, 0.039],[1.073, 0.089],[1.049, 0.127]]
	if _eta>-2.17 and _eta<=-1.80: idIsoSFbyPt = [[0.853, 0.028],[0.869, 0.025],[0.891, 0.016],[0.916, 0.014],[0.935, 0.009],[0.946, 0.012],[0.957, 0.011],[0.955, 0.054],[0.978, 0.019],[0.968, 0.016],[0.987, 0.022],[1.022, 0.022]]
	if _eta>-1.80 and _eta<=-1.57: idIsoSFbyPt = [[0.905, 0.074],[0.898, 0.024],[0.912, 0.052],[0.919, 0.026],[0.933, 0.004],[0.952, 0.005],[0.962, 0.005],[0.969, 0.045],[0.945, 0.078],[0.989, 0.046],[1.005, 0.077],[0.974, 0.056]]
	if _eta>-1.57 and _eta<=-1.44: idIsoSFbyPt = [[0.832, 0.233],[0.899, 0.39],[0.939, 0.221],[0.948, 0.096],[0.948, 0.009],[0.945, 0.021],[0.947, 0.031],[0.929, 0.052],[0.979, 0.124],[1.022, 0.089],[0.995, 0.047],[1.009, 0.051]]
	if _eta>-1.44 and _eta<=-0.80: idIsoSFbyPt = [[0.921, 0.055],[0.905, 0.032],[0.923, 0.016],[0.94, 0.02],[0.945, 0.005],[0.952, 0.011],[0.951, 0.017],[0.952, 0.009],[0.967, 0.043],[0.971, 0.01],[0.972, 0.053],[0.97, 0.021]]
	if _eta>-0.80 and _eta<=0.00 : idIsoSFbyPt = [[0.921, 0.047],[0.911, 0.034],[0.93, 0.033],[0.943, 0.016],[0.945, 0.004],[0.95, 0.011],[0.952, 0.013],[0.951, 0.009],[0.956, 0.025],[0.978, 0.009],[0.964, 0.02],[0.97, 0.049]]
	if _eta>0.00  and _eta<=0.80 : idIsoSFbyPt = [[0.936, 0.047],[0.943, 0.034],[0.951, 0.033],[0.964, 0.016],[0.966, 0.004],[0.968, 0.011],[0.967, 0.013],[0.973, 0.009],[0.975, 0.025],[0.993, 0.009],[0.992, 0.02],[0.986, 0.049]]
	if _eta>0.80  and _eta<=1.44 : idIsoSFbyPt = [[0.915, 0.055],[0.937, 0.032],[0.936, 0.016],[0.948, 0.02],[0.951, 0.005],[0.957, 0.011],[0.957, 0.017],[0.966, 0.009],[0.964, 0.043],[0.987, 0.01],[0.997, 0.053],[0.991, 0.021]]
	if _eta>1.44  and _eta<=1.57 : idIsoSFbyPt = [[0.855, 0.234],[0.915, 0.39],[0.908, 0.221],[0.938, 0.096],[0.947, 0.009],[0.931, 0.021],[0.942, 0.031],[0.896, 0.052],[0.934, 0.124],[0.984, 0.089],[0.934, 0.046],[1.019, 0.051]]
	if _eta>1.57  and _eta<=1.80 : idIsoSFbyPt = [[0.907, 0.074],[0.906, 0.024],[0.92, 0.052],[0.939, 0.026],[0.949, 0.004],[0.958, 0.005],[0.967, 0.005],[0.975, 0.045],[0.965, 0.078],[0.981, 0.046],[0.983, 0.077],[0.978, 0.056]]
	if _eta>1.80  and _eta<=2.17 : idIsoSFbyPt = [[0.877, 0.028],[0.887, 0.025],[0.902, 0.016],[0.924, 0.014],[0.945, 0.009],[0.957, 0.012],[0.963, 0.011],[0.965, 0.054],[0.978, 0.019],[0.991, 0.016],[1.024, 0.022],[1.0, 0.021]]
	if _eta>2.17  and _eta<=2.50 : idIsoSFbyPt = [[0.823, 0.039],[0.836, 0.129],[0.871, 0.054],[0.903, 0.021],[0.92, 0.018],[0.935, 0.017],[0.949, 0.044],[0.966, 0.033],[0.982, 0.091],[1.003, 0.038],[0.981, 0.089],[1.024, 0.126]]

	if _eta>-2.50 and _eta<=-2.17: hlt1SFbyPt = [[0.105,0.114],[0.467,0.048],[0.936,0.01],[0.978,0.003],[0.986,0.005],[0.995,0.013],[0.998,0.007],[0.998,0.057],[0.996,0.012],[1.004,0.018],[1.023,0.04],[0.995,0.008]]
	if _eta>-2.17 and _eta<=-1.80: hlt1SFbyPt = [[0.427,0.321],[0.763,0.047],[0.998,0.012],[1.004,0.004],[1.004,0.004],[1.002,0.002],[1.002,0.003],[0.999,0.014],[1.002,0.011],[1.001,0.006],[1.003,0.008],[0.998,0.004]]
	if _eta>-1.80 and _eta<=-1.57: hlt1SFbyPt = [[0.8,0.207],[0.928,0.083],[0.996,0.016],[0.997,0.011],[1.001,0.009],[1.001,0.002],[1.001,0.003],[0.998,0.002],[1.004,0.014],[0.998,0.005],[0.996,0.007],[1.008,0.017]]
	if _eta>-1.57 and _eta<=-1.44: hlt1SFbyPt = [[1,0.063],[0.94,0.026],[0.997,0.071],[1.003,0.006],[0.995,0.044],[0.994,0.003],[0.994,0.003],[0.997,0.035],[1.048,0.105],[1.011,0.042],[0.969,0.038],[0.963,0.321]]
	if _eta>-1.44 and _eta<=-0.80: hlt1SFbyPt = [[0.733,1.109],[0.914,0.027],[0.991,0.022],[0.994,0.002],[0.992,0.002],[0.992,0.003],[0.991,0.002],[0.99,0.004],[0.987,0.009],[0.991,0.003],[0.99,0.01],[0.988,0.007]]
	if _eta>-0.80 and _eta<=0.00 : hlt1SFbyPt = [[2.429,0.57],[0.998,0.046],[0.999,0.003],[0.993,0.003],[0.993,0.004],[0.99,0.003],[0.99,0.002],[0.99,0.002],[0.991,0.01],[0.992,0.024],[0.992,0.014],[0.989,0.015]]
	if _eta>0.00  and _eta<=0.80 : hlt1SFbyPt = [[1.308,0.57],[0.943,0.046],[0.984,0.003],[0.982,0.003],[0.981,0.004],[0.979,0.003],[0.981,0.002],[0.979,0.002],[0.979,0.01],[0.979,0.024],[0.982,0.014],[0.98,0.015]]
	if _eta>0.80  and _eta<=1.44 : hlt1SFbyPt = [[0.667,1.109],[0.839,0.027],[0.991,0.022],[0.993,0.002],[0.992,0.002],[0.993,0.003],[0.991,0.002],[0.988,0.004],[0.988,0.009],[0.99,0.003],[0.988,0.01],[0.985,0.007]]
	if _eta>1.44  and _eta<=1.57 : hlt1SFbyPt = [[0.702,0.063],[0.85,0.026],[0.995,0.071],[1.001,0.006],[1.003,0.044],[0.998,0.003],[1.003,0.003],[1.014,0.035],[1.006,0.105],[1.017,0.042],[0.993,0.038],[0.971,0.321]]
	if _eta>1.57  and _eta<=1.80 : hlt1SFbyPt = [[0.897,0.205],[0.847,0.083],[1.001,0.016],[1.007,0.011],[1.004,0.009],[1.004,0.002],[1.001,0.003],[1.004,0.002],[1.007,0.014],[0.998,0.005],[1.0,0.007],[1.009,0.017]]
	if _eta>1.80  and _eta<=2.17 : hlt1SFbyPt = [[0.275,0.321],[0.687,0.047],[0.99,0.012],[1.002,0.004],[1.002,0.004],[1.001,0.002],[1.0,0.003],[1.0,0.014],[0.999,0.011],[0.998,0.006],[1.003,0.008],[1.003,0.004]]
	if _eta>2.17  and _eta<=2.50 : hlt1SFbyPt = [[0.101,0.114],[0.422,0.048],[0.901,0.01],[0.965,0.003],[0.983,0.005],[0.99,0.013],[0.998,0.007],[0.993,0.057],[1.0,0.012],[1.006,0.018],[1.024,0.04],[0.99,0.008]]

	if _eta>-2.50 and _eta<=-2.17: hlt2SFbyPt = [[0.911,0.021],[0.932,0.007],[0.958,0.008],[0.978,0.004],[0.986,0.005],[0.995,0.013],[0.998,0.007],[0.998,0.057],[0.996,0.012],[1.004,0.018],[1.023,0.04],[0.996,0.008]]
	if _eta>-2.17 and _eta<=-1.80: hlt2SFbyPt = [[0.994,0.022],[1.002,0.027],[1.003,0.011],[1.004,0.004],[1.004,0.004],[1.002,0.002],[1.002,0.003],[0.999,0.014],[1.002,0.011],[1.001,0.006],[1.003,0.008],[0.998,0.004]]
	if _eta>-1.80 and _eta<=-1.57: hlt2SFbyPt = [[0.983,0.119],[0.987,0.036],[1.0,0.013],[0.996,0.011],[1.001,0.008],[1.001,0.002],[1.001,0.003],[0.998,0.002],[1.004,0.014],[0.998,0.005],[0.995,0.007],[1.008,0.017]]
	if _eta>-1.57 and _eta<=-1.44: hlt2SFbyPt = [[1.023,0.02],[1.015,0.037],[1.003,0.026],[1.002,0.006],[0.995,0.045],[0.994,0.003],[0.995,0.003],[0.995,0.035],[1.045,0.105],[1.011,0.041],[0.969,0.038],[0.963,0.321]]
	if _eta>-1.44 and _eta<=-0.80: hlt2SFbyPt = [[0.987,0.035],[0.992,0.007],[0.993,0.018],[0.994,0.002],[0.992,0.001],[0.992,0.003],[0.991,0.002],[0.99,0.004],[0.987,0.009],[0.992,0.003],[0.99,0.01],[0.988,0.007]]
	if _eta>-0.80 and _eta<=0.00 : hlt2SFbyPt = [[0.979,0.012],[0.998,0.02],[0.999,0.004],[0.993,0.002],[0.993,0.004],[0.99,0.003],[0.99,0.002],[0.99,0.002],[0.991,0.01],[0.992,0.024],[0.992,0.014],[0.989,0.015]]
	if _eta>0.00  and _eta<=0.80 : hlt2SFbyPt = [[0.974,0.012],[0.981,0.02],[0.985,0.004],[0.982,0.002],[0.981,0.004],[0.979,0.003],[0.982,0.002],[0.979,0.002],[0.979,0.01],[0.979,0.024],[0.982,0.014],[0.981,0.015]]
	if _eta>0.80  and _eta<=1.44 : hlt2SFbyPt = [[0.987,0.035],[0.98,0.007],[0.995,0.018],[0.993,0.002],[0.992,0.001],[0.993,0.003],[0.991,0.002],[0.988,0.004],[0.988,0.009],[0.99,0.003],[0.988,0.01],[0.984,0.007]]
	if _eta>1.44  and _eta<=1.57 : hlt2SFbyPt = [[0.985,0.02],[1.021,0.037],[1.008,0.026],[1.002,0.006],[1.003,0.045],[0.999,0.003],[1.003,0.003],[1.014,0.035],[1.007,0.105],[1.018,0.042],[0.992,0.039],[0.971,0.321]]
	if _eta>1.57  and _eta<=1.80 : hlt2SFbyPt = [[0.98,0.12],[1.03,0.036],[1.005,0.013],[1.007,0.011],[1.003,0.008],[1.004,0.002],[1.001,0.003],[1.004,0.002],[1.007,0.014],[0.998,0.005],[1.0,0.007],[1.009,0.017]]
	if _eta>1.80  and _eta<=2.17 : hlt2SFbyPt = [[0.983,0.022],[0.995,0.027],[0.996,0.011],[1.01,0.004],[1.002,0.004],[1.001,0.002],[1.0,0.003],[1.0,0.014],[0.999,0.011],[0.998,0.006],[1.004,0.008],[1.003,0.004]]
	if _eta>2.17  and _eta<=2.50 : hlt2SFbyPt = [[0.854,0.02],[0.886,0.007],[0.922,0.008],[0.966,0.004],[0.983,0.005],[0.99,0.013],[0.998,0.007],[0.992,0.057],[1.001,0.012],[1.006,0.018],[1.025,0.04],[0.99,0.008]]


	idIsoSFs = idIsoSFbyPt[index]
	idIsoSF = idIsoSFs[0]
	idIsoSFup   = idIsoSFs[0]+idIsoSFs[1]
	idIsoSFdown = max(idIsoSFs[0]-idIsoSFs[1],0.0)

	hlt1SFs = hlt1SFbyPt[index]
	hlt1SF = hlt1SFs[0]
	hlt1SFup   = hlt1SFs[0]+hlt1SFs[1]
	hlt1SFdown = max(hlt1SFs[0]-hlt1SFs[1],0.0)

	hlt2SFs = hlt2SFbyPt[index]
	hlt2SF = hlt2SFs[0]
	hlt2SFup   = hlt2SFs[0]+hlt2SFs[1]
	hlt2SFdown = max(hlt2SFs[0]-hlt2SFs[1],0.0)

	return [idIsoSF,idIsoSFup,idIsoSFdown,hlt1SF,hlt1SFup,hlt1SFdown,hlt2SF,hlt2SFup,hlt2SFdown]


def getElectronEffectiveArea(eta):
	abseta=abs(eta)
	eA = 1.
	if abseta>0.0000 and abseta<1.0000 : eA=0.1703
	if abseta>1.0000 and abseta<1.4790 : eA=0.1715
	if abseta>1.4790 and abseta<2.0000 : eA=0.1213
	if abseta>2.0000 and abseta<2.2000 : eA=0.1230
	if abseta>2.2000 and abseta<2.3000 : eA=0.1635
	if abseta>2.3000 and abseta<2.4000 : eA=0.1937
	if abseta>2.4000 and abseta<5.0000 : eA=0.2393
	return eA



def JERModifiedPt(pt,eta,phi,T,modtype):
	# Pupose: Modify reco jets based on genjets. Input is pt/eta/phi of a jet.
	#         The jet will be matched to a gen jet, and the difference
	#         between reco and gen will be modified according to appropriate
	#         pt/eta dependent scale factors.
	#         The modified jet PT is returned.
	#         https://hypernews.cern.ch/HyperNews/CMS/get/JetMET/1336.html
	#         https://twiki.cern.ch/twiki/bin/view/CMS/JetResolution

	if T.run>1:
		return pt

	bestn = -1
	bestdpt = 0.
	bestdR = 9999999.9
	jet = TLorentzVector()
	jet.SetPtEtaPhiM(pt,eta,phi,0.0)
	for n in range(len(T.GenJet_pt)):
		gjet = TLorentzVector()
		gjet.SetPtEtaPhiM(T.GenJet_pt[n],T.GenJet_eta[n],T.GenJet_phi[n],T.GenJet_mass[n])
		dR = abs(jet.DeltaR(gjet))
		if dR<bestdR and dR<0.3 :
			bestdR = dR
			bestn = n
			bestdpt = pt-gjet.Pt()

	if bestdR>0.5:
		return pt

	abseta = abs(eta)

	#13 TeV 80X (2016, BCD+GH PromtReco) DATA/MC SFs
	if abseta >= 0   : jfacs = [  0.109 , 0.117 , 0.101  ]
	if abseta >= 0.5 : jfacs = [  0.138 , 0.151 , 0.125  ]
	if abseta >= 0.8 : jfacs = [  0.114 , 0.127 , 0.101  ]
	if abseta >= 1.1 : jfacs = [  0.123 , 0.147 , 0.099  ]
	if abseta >= 1.3 : jfacs = [  0.084 , 0.095 , 0.073  ]
	if abseta >= 1.7 : jfacs = [  0.082 , 0.117 , 0.047  ]
	if abseta >= 1.9 : jfacs = [  0.140 , 0.187 , 0.093  ]
	if abseta >= 2.1 : jfacs = [  0.067 , 0.120 , 0.014  ]
	if abseta >= 2.3 : jfacs = [  0.177 , 0.218 , 0.136  ]
	if abseta >= 2.5 : jfacs = [  0.364 , 0.403 , 0.325  ]
	if abseta >= 2.8 : jfacs = [  0.857 , 0.928 , 0.786  ]
	if abseta >= 3.0 : jfacs = [  0.328 , 0.350 , 0.306  ]
	if abseta >= 3.2 : jfacs = [  0.160 , 0.189 , 0.131  ]

	if modtype == '':
		adjustmentfactor = jfacs[0]
	if modtype == 'up':
		adjustmentfactor = jfacs[1]
	if modtype == 'down':
		adjustmentfactor = jfacs[2]

	ptadjustment = adjustmentfactor*bestdpt
	pt += ptadjustment
	return max(0.,pt)


def LooseIDJets(T,met,variation,isdata):
	# Pupose: Gets the collection of jets passing loose PFJet ID.
	#         Returns jets as TLorentzVectors, and indices corrresponding
	#         to the surviving jetss of the jet collection.
	#         Also returns modified MET for systematic variations.

        _PFJetPt = [pt for pt in T.Jet_pt]
	
        if variation=='JERup':
		#_PFJetPt = [JERModifiedPt(T.Jet_pt[n],T.Jet_eta[n],T.Jet_phi[n],T,'up') for n in range(len(T.Jet_pt))] #old way
                _PFJetPt = [pt for pt in T.Jet_pt_jerUp] 
	if variation=='JERdown':
		#_PFJetPt = [JERModifiedPt(T.Jet_pt[n],T.Jet_eta[n],T.Jet_phi[n],T,'down') for n in range(len(T.Jet_pt))] #old way
                _PFJetPt = [pt for pt in T.Jet_pt_jerDown]               

	#print 'JEC:'
	#print [T.PFJetJECUncAK4CHS[n] for n in range(len(_PFJetPt))]
	#print '\n'

	if variation=='JESup':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTotalUp] 
	if variation=='JESdown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTotalDown]

	if variation=='JESAbsoluteMPFBiasUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteMPFBiasUp]
	if variation=='JESAbsoluteMPFBiasDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteMPFBiasDown]
	if variation=='JESAbsoluteScaleUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteScaleUp]
	if variation=='JESAbsoluteScaleDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteScaleDown]
	if variation=='JESAbsoluteStatUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteStatUp]
	if variation=='JESAbsoluteStatDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteStatDown]
	if variation=='JESFlavorQCDUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFlavorQCDUp]
	if variation=='JESFlavorQCDDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFlavorQCDDown]
	if variation=='JESFragmentationUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFragmentationUp]
	if variation=='JESFragmentationDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFragmentationDown]
	if variation=='JESPileUpDataMCUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpDataMCUp]
	if variation=='JESPileUpDataMCDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpDataMCDown]
	if variation=='JESPileUpPtBBUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtBBUp]
	if variation=='JESPileUpPtBBDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtBBDown]
	if variation=='JESPileUpPtEC1Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC1Up]
	if variation=='JESPileUpPtEC1Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC1Down]
	if variation=='JESPileUpPtEC2Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC2Up]
	if variation=='JESPileUpPtEC2Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC2Down]
	if variation=='JESPileUpPtHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtHFUp]
	if variation=='JESPileUpPtHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtHFDown]
	if variation=='JESPileUpPtRefUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtRefUp]
	if variation=='JESPileUpPtRefDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtRefDown]
	if variation=='JESRelativeBalUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeBalUp]
	if variation=='JESRelativeBalDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeBalDown]
	if variation=='JESRelativeFSRUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeFSRUp]
	if variation=='JESRelativeFSRDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeFSRDown]
	if variation=='JESRelativeJEREC1Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC1Up]
	if variation=='JESRelativeJEREC1Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC1Down]
	if variation=='JESRelativeJEREC2Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC2Up]
	if variation=='JESRelativeJEREC2Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC2Down]
	if variation=='JESRelativeJERHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJERHFUp]
	if variation=='JESRelativeJERHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJERHFDown]
	if variation=='JESRelativePtBBUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtBBUp]
	if variation=='JESRelativePtBBDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtBBDown]
	if variation=='JESRelativePtEC1Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC1Up]
	if variation=='JESRelativePtEC1Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC1Down]
	if variation=='JESRelativePtEC2Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC2Up]
	if variation=='JESRelativePtEC2Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC2Down]
	if variation=='JESRelativePtHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtHFUp]
	if variation=='JESRelativePtHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtHFDown]
	if variation=='JESRelativeStatECUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatECUp]
	if variation=='JESRelativeStatECDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatECDown]
	if variation=='JESRelativeStatFSRUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatFSRUp]
	if variation=='JESRelativeStatFSRDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatFSRDown]
	if variation=='JESRelativeStatHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatHFUp]
	if variation=='JESRelativeStatHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatHFDown]
	if variation=='JESSinglePionECALUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionECALUp]
	if variation=='JESSinglePionECALDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionECALDown]
	if variation=='JESSinglePionHCALUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionHCALUp]
	if variation=='JESSinglePionHCALDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionHCALDown]
	if variation=='JESTimePtEtaUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTimePtEtaUp]
	if variation=='JESTimePtEtaDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTimePtEtaDown]

	if (isdata):
		_PFJetPt = [pt for pt in T.Jet_pt]

	# print met.Pt(),


	JetFailThreshold=0.0

	jets = []
	jetinds = []
	bTagRegSFs = []
	NHFs = []
	NEMFs = []
	CSVscores,bMVAscores = [],[]
	bTagSFsLoose, bTagSFsMed = [],[] #[central,up,down]
	bTagSFsLoose_csv, bTagSFsMed_csv = [],[] #[central,up,down]
	for n in range(len(_PFJetPt)):
		looseJetID = False
		eta = T.Jet_eta[n]
		NHF = T.Jet_neHEF[n]
		NEMF = T.Jet_neEmEF[n]
		CEMF = T.Jet_chEmEF[n]
		CHF = T.Jet_chHEF[n]
#?		MUF = T.PFJetMuonEnergyFractionAK4CHS[n]
#?		NumConst = T.PFJetChargedMultiplicityAK4CHS[n]+T.PFJetNeutralMultiplicityAK4CHS[n]
#?		NumNeutralParticle = T.PFJetNeutralMultiplicityAK4CHS[n]
#?		CHM = T.PFJetChargedMultiplicityAK4CHS[n]

		looseJetID = (T.Jet_jetId[n] & 0x2)
#		looseJetID = (abs(eta)<2.4 and NHF<0.99 and NEMF<0.99 and NumConst>1 and CHF>0 and CHM>0 and CEMF<0.99)
		#if abs(eta)<=2.7:
		#	looseJetID = (NHF<0.99 and NEMF<0.99 and NumConst>1) and ((abs(eta)<=2.4 and CHF>0 and CHM>0 and CEMF<0.99) or abs(eta)>2.4) and abs(eta)<=2.7
		#elif abs(eta)<=3.0:
		#	looseJetID = (NHF< 0.98 and NEMF>0.01 and NumNeutralParticle>2 and abs(eta)>2.7 and abs(eta)<=3.0 )
		#else:
		#	looseJetID = (NEMF<0.90 and NumNeutralParticle>10 and abs(eta)>3.0 and abs(eta)<5.0 )
		if _PFJetPt[n]>20 :#fixme todo was pt>30, reduced for HH
			if looseJetID:
				j = TLorentzVector()
				j.SetPtEtaPhiM(_PFJetPt[n],T.Jet_eta[n],T.Jet_phi[n],T.Jet_mass[n])
				oldjet = TLorentzVector()
				oldjet.SetPtEtaPhiM(T.Jet_pt[n],T.Jet_eta[n],T.Jet_phi[n],T.Jet_mass[n])
				met = PropagatePTChangeToMET(met,oldjet,j)
				jets.append(j)
				jetinds.append(n)
				NHFs.append(NHF)
				NEMFs.append(NEMF)
				CSVscores.append(T.Jet_btagCSVV2[n])
				bMVAscores.append(T.Jet_btagCMVA[n])
				bTagRegSFs.append(T.Jet_bRegCorr[n])

				# b-tag SF
				flavor = -1
				if isdata==False:
					flavor = abs(T.Jet_hadronFlavour[n])#updated to HadronFlavour
				#print flavor
				if flavor in [0,1,2,3,21]: flavor=2
				if flavor == 4 : flavor=1
				if flavor == 5 : flavor=0
				ptSF=T.Jet_pt[n]
				etaSF=abs(eta)
				if etaSF>=2.4: etaSF=2.399
				sf_loose, sf_loose_up, sf_loose_down, sf_medium, sf_medium_up, sf_medium_down=1.,1.,1.,1.,1.,1.
				if not isdata:
					sf_loose = readerLoose.eval_auto_bounds(
						'central',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_loose_up = readerLoose.eval_auto_bounds(
						'up',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_loose_down = readerLoose.eval_auto_bounds(
						'down',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_medium = readerMed.eval_auto_bounds(
						'central',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_medium_up = readerMed.eval_auto_bounds(
						'up',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_medium_down = readerMed.eval_auto_bounds(
						'down',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
				bTagSFsLoose.append([sf_loose,sf_loose_up,sf_loose_down])

                                #FIXME moving to nanoAOD post-processing version - for 2016 its CSVv2 medium
                                #bTagSFsMed.append([sf_medium,sf_medium_up,sf_medium_down])
				if isData:
					bTagSFsMed.append([1.0, 1.0, 1.0])
				else:
					bTagSFsMed.append([T.Jet_btagSF[n], T.Jet_btagSF_up[n], T.Jet_btagSF_down[n]])
                                #

                                sf_loose_csv, sf_loose_csv_up, sf_loose_csv_down, sf_medium_csv, sf_medium_csv_up, sf_medium_csv_down=1.,1.,1.,1.,1.,1.
				bTagSFsLoose_csv.append([sf_loose_csv,sf_loose_csv_up,sf_loose_csv_down])
				bTagSFsMed_csv.append([sf_medium_csv,sf_medium_csv_up,sf_medium_csv_down])
				#if T.PFJetCombinedMVABTagAK4CHS[n]>-0.5884:
				#	print flavor,abs(T.PFJetEtaAK4CHS[n]),T.PFJetPtAK4CHS[n]
				#	print 'loose:',sf_loose,sf_loose_up,sf_loose_down
				#	print 'medium:',sf_medium,sf_medium_up,sf_medium_down,'\n'

			else:
				if _PFJetPt[n] > JetFailThreshold:
					JetFailThreshold = _PFJetPt[n]

	# print met.Pt()

	return [jets,jetinds,met,JetFailThreshold,NHFs,NEMFs,CSVscores,bMVAscores,bTagSFsLoose,bTagSFsMed,bTagSFsLoose_csv,bTagSFsMed_csv,bTagRegSFs]

def AK8LooseIDJets(T,met,variation,isdata):
	# Pupose: Gets the collection of jets passing loose PFJet ID.
	#         Returns jets as TLorentzVectors, and indices corrresponding
	#         to the surviving jetss of the jet collection.
	#         Also returns modified MET for systematic variations.

	if variation!='JERup' and variation!='JERdown':
		# _PFJetPt = [JERModifiedPt(T.PFJetPt[n],T.PFJetEta[n],T.PFJetPhi[n],T,'') for n in range(len(T.PFJetPt))]
		 _PFJetPt = [pt for pt in T.FatJet_pt]
	if variation=='JERup':
		_PFJetPt = [JERModifiedPt(T.FatJet_pt[n],T.FatJet_eta[n],T.FatJet_phi[n],T,'up') for n in range(len(T.FatJet_pt))]
	if variation=='JERdown':
		_PFJetPt = [JERModifiedPt(T.FatJet_pt[n],T.FatJet_eta[n],T.FatJet_phi[n],T,'down') for n in range(len(T.FatJet_pt))]

	#print 'JEC:'
	#print [T.PFJetJECUncAK4CHS[n] for n in range(len(_PFJetPt))]
	#print '\n'

	if variation=='JESup':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTotalUp] 
	if variation=='JESdown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTotalDown]

	if variation=='JESAbsoluteMPFBiasUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteMPFBiasUp]
	if variation=='JESAbsoluteMPFBiasDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteMPFBiasDown]
	if variation=='JESAbsoluteScaleUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteScaleUp]
	if variation=='JESAbsoluteScaleDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteScaleDown]
	if variation=='JESAbsoluteStatUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteStatUp]
	if variation=='JESAbsoluteStatDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesAbsoluteStatDown]
	if variation=='JESFlavorQCDUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFlavorQCDUp]
	if variation=='JESFlavorQCDDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFlavorQCDDown]
	if variation=='JESFragmentationUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFragmentationUp]
	if variation=='JESFragmentationDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesFragmentationDown]
	if variation=='JESPileUpDataMCUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpDataMCUp]
	if variation=='JESPileUpDataMCDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpDataMCDown]
	if variation=='JESPileUpPtBBUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtBBUp]
	if variation=='JESPileUpPtBBDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtBBDown]
	if variation=='JESPileUpPtEC1Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC1Up]
	if variation=='JESPileUpPtEC1Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC1Down]
	if variation=='JESPileUpPtEC2Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC2Up]
	if variation=='JESPileUpPtEC2Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtEC2Down]
	if variation=='JESPileUpPtHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtHFUp]
	if variation=='JESPileUpPtHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtHFDown]
	if variation=='JESPileUpPtRefUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtRefUp]
	if variation=='JESPileUpPtRefDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesPileUpPtRefDown]
	if variation=='JESRelativeBalUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeBalUp]
	if variation=='JESRelativeBalDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeBalDown]
	if variation=='JESRelativeFSRUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeFSRUp]
	if variation=='JESRelativeFSRDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeFSRDown]
	if variation=='JESRelativeJEREC1Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC1Up]
	if variation=='JESRelativeJEREC1Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC1Down]
	if variation=='JESRelativeJEREC2Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC2Up]
	if variation=='JESRelativeJEREC2Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJEREC2Down]
	if variation=='JESRelativeJERHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJERHFUp]
	if variation=='JESRelativeJERHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeJERHFDown]
	if variation=='JESRelativePtBBUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtBBUp]
	if variation=='JESRelativePtBBDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtBBDown]
	if variation=='JESRelativePtEC1Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC1Up]
	if variation=='JESRelativePtEC1Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC1Down]
	if variation=='JESRelativePtEC2Up':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC2Up]
	if variation=='JESRelativePtEC2Down':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtEC2Down]
	if variation=='JESRelativePtHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtHFUp]
	if variation=='JESRelativePtHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativePtHFDown]
	if variation=='JESRelativeStatECUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatECUp]
	if variation=='JESRelativeStatECDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatECDown]
	if variation=='JESRelativeStatFSRUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatFSRUp]
	if variation=='JESRelativeStatFSRDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatFSRDown]
	if variation=='JESRelativeStatHFUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatHFUp]
	if variation=='JESRelativeStatHFDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesRelativeStatHFDown]
	if variation=='JESSinglePionECALUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionECALUp]
	if variation=='JESSinglePionECALDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionECALDown]
	if variation=='JESSinglePionHCALUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionHCALUp]
	if variation=='JESSinglePionHCALDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesSinglePionHCALDown]
	if variation=='JESTimePtEtaUp':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTimePtEtaUp]
	if variation=='JESTimePtEtaDown':
		_PFJetPt = [pt for pt in T.Jet_pt_jesTimePtEtaDown]

	if (isdata):
		_PFJetPt = [pt for pt in T.FatJet_pt]
		#_PFJetPt = [T.PFJetPtAK4CHS[n]*T.PFJetL2L3ResJECAK4CHS[n] for n in range(len(T.PFJetPtAK4CHS))]

	# print met.Pt(),


	JetFailThreshold=0.0

	jets = []
	jetinds = []
	bTagRegSFs = []
	NHFs = []
	NEMFs = []
	CSVscores,bMVAscores = [],[]
	bTagSFsLoose, bTagSFsMed = [],[] #[central,up,down]
	bTagSFsLoose_csv, bTagSFsMed_csv = [],[] #[central,up,down]
	for n in range(len(_PFJetPt)):
		looseJetID = False
		eta = T.FatJet_eta[n]
#?		NHF = T.Jet_neHEF[n]
#?		NEMF = T.Jet_neEmEF[n]
#?		CEMF = T.Jet_chEmEF[n]
#?		CHF = T.Jet_chHEF[n]
#?		MUF = T.PFJetMuonEnergyFractionAK4CHS[n]
#?		NumConst = T.PFJetChargedMultiplicityAK4CHS[n]+T.PFJetNeutralMultiplicityAK4CHS[n]
#?		NumNeutralParticle = T.PFJetNeutralMultiplicityAK4CHS[n]
#?		CHM = T.PFJetChargedMultiplicityAK4CHS[n]

		looseJetID = (T.FatJet_jetId[n] & 0x2)
#		looseJetID = (abs(eta)<2.4 and NHF<0.99 and NEMF<0.99 and NumConst>1 and CHF>0 and CHM>0 and CEMF<0.99)
		#if abs(eta)<=2.7:
		#	looseJetID = (NHF<0.99 and NEMF<0.99 and NumConst>1) and ((abs(eta)<=2.4 and CHF>0 and CHM>0 and CEMF<0.99) or abs(eta)>2.4) and abs(eta)<=2.7
		#elif abs(eta)<=3.0:
		#	looseJetID = (NHF< 0.98 and NEMF>0.01 and NumNeutralParticle>2 and abs(eta)>2.7 and abs(eta)<=3.0 )
		#else:
		#	looseJetID = (NEMF<0.90 and NumNeutralParticle>10 and abs(eta)>3.0 and abs(eta)<5.0 )
		if _PFJetPt[n]>20 :#fixme todo was pt>30, reduced for HH
			if looseJetID:
				j = TLorentzVector()
				j.SetPtEtaPhiM(_PFJetPt[n],T.FatJet_eta[n],T.FatJet_phi[n],T.FatJet_mass[n])
				oldjet = TLorentzVector()
				oldjet.SetPtEtaPhiM(T.FatJet_pt[n],T.FatJet_eta[n],T.FatJet_phi[n],T.FatJet_mass[n])
				met = PropagatePTChangeToMET(met,oldjet,j)
				jets.append(j)
				jetinds.append(n)
				NHFs.append(NHF)
				NEMFs.append(NEMF)
				CSVscores.append(T.FatJet_btagCSVV2[n])
				bMVAscores.append(T.FatJet_btagCMVA[n])
#				bTagRegSFs.append(T.Jet_bRegCorr[n])

				# b-tag SF
				flavor = abs(T.Jet_hadronFlavour[n])#updated to HadronFlavour
				#print flavor
				if flavor in [0,1,2,3,21]: flavor=2
				if flavor == 4 : flavor=1
				if flavor == 5 : flavor=0
				ptSF=T.Jet_pt[n]
				etaSF=abs(eta)
				if etaSF>=2.4: etaSF=2.399
				sf_loose, sf_loose_up, sf_loose_down, sf_medium, sf_medium_up, sf_medium_down=1.,1.,1.,1.,1.,1.
				if not isdata:
					sf_loose = readerLoose.eval_auto_bounds(
						'central',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_loose_up = readerLoose.eval_auto_bounds(
						'up',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_loose_down = readerLoose.eval_auto_bounds(
						'down',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_medium = readerMed.eval_auto_bounds(
						'central',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_medium_up = readerMed.eval_auto_bounds(
						'up',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
					sf_medium_down = readerMed.eval_auto_bounds(
						'down',      # systematic (here also 'up'/'down' possible)
						flavor,                    # jet flavor
						etaSF,  # eta
						ptSF         # pt
						)
				bTagSFsLoose.append([sf_loose,sf_loose_up,sf_loose_down])
				bTagSFsMed.append([sf_medium,sf_medium_up,sf_medium_down])
				sf_loose_csv, sf_loose_csv_up, sf_loose_csv_down, sf_medium_csv, sf_medium_csv_up, sf_medium_csv_down=1.,1.,1.,1.,1.,1.
				bTagSFsLoose_csv.append([sf_loose_csv,sf_loose_csv_up,sf_loose_csv_down])
				bTagSFsMed_csv.append([sf_medium_csv,sf_medium_csv_up,sf_medium_csv_down])
				#if T.PFJetCombinedMVABTagAK4CHS[n]>-0.5884:
				#	print flavor,abs(T.PFJetEtaAK4CHS[n]),T.PFJetPtAK4CHS[n]
				#	print 'loose:',sf_loose,sf_loose_up,sf_loose_down
				#	print 'medium:',sf_medium,sf_medium_up,sf_medium_down,'\n'

			else:
				if _PFJetPt[n] > JetFailThreshold:
					JetFailThreshold = _PFJetPt[n]

	# print met.Pt()

	return [jets,jetinds,met,JetFailThreshold,NHFs,NEMFs,CSVscores,bMVAscores,bTagSFsLoose,bTagSFsMed,bTagSFsLoose_csv,bTagSFsMed_csv,bTagRegSFs]



def GetHHJetsNew(jets,btagScoresCSV,btagScoresMVA,bTagSFloose,bTagSFmed,bTagSFloose_csv,bTagSFmed_csv,bTagRegSFs,muon1,muon2,electron1,electron2,isMuEvent,isEleEvent,jetinds, T, met):
	#Purpose: select which jets to use for HH analysis, separating bJets from light jets. Note that jets have already been cleaned from muons and electrons in cone of 0.3.

	EmptyLorentz = TLorentzVector()
	EmptyLorentz.SetPtEtaPhiM(0,0,0,0)

	if isMuEvent:
		[lepton1, lepton2] = [muon1,muon2]
	elif isEleEvent:
		[lepton1, lepton2] = [electron1,electron2]
	else:
		[lepton1, lepton2] = [EmptyLorentz,EmptyLorentz]

	[bjet1,bjet2,jet1,jet2,jet3]=[EmptyLorentz,EmptyLorentz,EmptyLorentz,EmptyLorentz,EmptyLorentz]
	regr_corrF1, regr_corrF2 = 1, 1
	#if v == '' : print len(jets)
	highBtagCSV,highBtag = -20.0,-20.0
	secondBtagCSV,secondBtag = -20.0,-20.0
	jet1CISV,jet2CISV,jet1CMVA,jet2CMVA = -20.0,-20.0,-20.0,-20.0
	highBtagCounter = -1
	secondBtagCounter = -1
	jet1index,jet2index = -1,-1
	indRecoBJet1 = -1
	indRecoBJet2 = -1
	indRecoJet1 = -1
	indRecoJet2 = -1
	indRecoJet3 = -1
	closestH = 2200. #999.
	closestZ = 2200. #175.
	gotBs = False
	gotZjs = False
	Hjet1BtagSFL,Hjet1BtagSFM=[1.,1.,1.],[1.,1.,1.]
	Hjet2BtagSFL,Hjet2BtagSFM=[1.,1.,1.],[1.,1.,1.]
	Zjet1BtagSFL,Zjet1BtagSFM=[1.,1.,1.],[1.,1.,1.]
	Zjet2BtagSFL,Zjet2BtagSFM=[1.,1.,1.],[1.,1.,1.]
	Hjet1BtagSFL_csv,Hjet1BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
	Hjet2BtagSFL_csv,Hjet2BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
	Zjet1BtagSFL_csv,Zjet1BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
	Zjet2BtagSFL_csv,Zjet2BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
	if not gotBs :
		highBtagCSV,highBtag = -20.0,-20.0
		secondBtagCSV,secondBtag = -20.0,-20.0
		jet1CISV,jet2CISV,jet1CMVA,jet2CMVA = -20.0,-20.0,-20.0,-20.0
		highBtagCounter = -1
		secondBtagCounter = -1
		indRecoBJet1 = -1
		indRecoBJet2 = -1
		Hjet1BtagSFL,Hjet1BtagSFM=[1.,1.,1.],[1.,1.,1.]
		Hjet2BtagSFL,Hjet2BtagSFM=[1.,1.,1.],[1.,1.,1.]
		Hjet1BtagSFL_csv,Hjet1BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
		Hjet2BtagSFL_csv,Hjet2BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]

		for i in range(len(btagScoresMVA)) :
			#if T.PFJetPartonFlavourAK4CHS[jetinds[i]] == 21 : continue  # for testing the effect of gluon jets
			if btagScoresMVA[i] < -0.5884 : continue # -0.5884 is Loose WP
			if i==jet1index or i==jet2index: continue
			if btagScoresMVA[i]>highBtag:
				highBtag = btagScoresMVA[i]
				highBtagCSV = btagScoresCSV[i]
				highBtagCounter = i
		for i in range(len(btagScoresMVA)) :
			#if T.PFJetPartonFlavourAK4CHS[jetinds[i]] == 21 : continue  # for testing the effect of gluon jets
			if btagScoresMVA[i] < -0.5884 : continue
			if i==jet1index or i==jet2index: continue
			if i==highBtagCounter: continue
			if btagScoresMVA[i]>secondBtag :
				secondBtag = btagScoresMVA[i]
				secondBtagCSV = btagScoresCSV[i]
				secondBtagCounter = i
		if highBtagCounter >= 0 :
			bjet1,indRecoBJet1 = jets[highBtagCounter],jetinds[highBtagCounter]
			regr_corrF1 = bTagRegSFs[highBtagCounter]
			highBtag,highBtagCSV  = btagScoresMVA[highBtagCounter],btagScoresCSV[highBtagCounter]
			Hjet1BtagSFL=bTagSFloose[highBtagCounter]
			Hjet1BtagSFM=bTagSFmed[highBtagCounter]
			Hjet1BtagSFL_csv=bTagSFloose_csv[highBtagCounter]
			Hjet1BtagSFM_csv=bTagSFmed_csv[highBtagCounter]
			if secondBtagCounter >= 0 :
				bjet2,indRecoBJet2 = jets[secondBtagCounter],jetinds[secondBtagCounter]
				regr_corrF2 = bTagRegSFs[secondBtagCounter]
				secondBtag,secondBtagCSV = btagScoresMVA[secondBtagCounter],btagScoresCSV[secondBtagCounter]
				Hjet2BtagSFL=bTagSFloose[secondBtagCounter]
				Hjet2BtagSFM=bTagSFmed[secondBtagCounter]
				Hjet2BtagSFL_csv=bTagSFloose_csv[secondBtagCounter]
				Hjet2BtagSFM_csv=bTagSFmed_csv[secondBtagCounter]
				gotBs = True
			else:
				for j in range(len(btagScoresMVA)) :
					#if T.PFJetPartonFlavourAK4CHS[jetinds[j]] == 21 : continue  # for testing the effect of gluon jets
					#if btagScoresCSV[j] < 0.06  and abs(-0.853212237358 - btagScoresMVA[j]) < 0.000000000002 : continue # if I want to include this condition I have to put somthing tighter, because there are bjets with this condition as well
					if j==jet1index or j==jet2index: continue
					if j==highBtagCounter: continue
					#if v == '' : print ' debug 1 high bscore : index i', jetinds[highBtagCounter], 'index j', jetinds[j],'m_bb',(jets[highBtagCounter]+jets[j]).M(), ' diff', abs((jets[highBtagCounter]+jets[j]).M()-125), 'dR', abs(jets[highBtagCounter].DeltaR(jets[j]))
					if abs((jets[highBtagCounter]+jets[j]).M()-125) < closestH and (jets[highBtagCounter]+jets[j]).M() > 0 :
						closestH = abs((jets[highBtagCounter]+jets[j]).M()-125)
						secondBtagCounter = j
						bjet2 = jets[j]
						indRecoBJet2 = jetinds[j]
						secondBtag = btagScoresMVA[j]
						secondBtagCSV = btagScoresCSV[j]
						Hjet2BtagSFL=bTagSFloose[j]
						Hjet2BtagSFM=bTagSFmed[j]
						Hjet2BtagSFL_csv=bTagSFloose_csv[j]
						Hjet2BtagSFM_csv=bTagSFmed_csv[j]
						gotBs = True

	if not gotBs :
		highBtagCSV,highBtag = -20.0,-20.0
		secondBtagCSV,secondBtag = -20.0,-20.0
		highBtagCounter = -1
		secondBtagCounter = -1
		indRecoBJet1 = -1
		indRecoBJet2 = -1
		Hjet1BtagSFL,Hjet1BtagSFM=[1.,1.,1.],[1.,1.,1.]
		Hjet2BtagSFL,Hjet2BtagSFM=[1.,1.,1.],[1.,1.,1.]
		Hjet1BtagSFL_csv,Hjet1BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
		Hjet2BtagSFL_csv,Hjet2BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]

		closestH = 2200 #2200. #50.
		for i in range(len(jets)-1) :
			#if T.PFJetPartonFlavourAK4CHS[jetinds[i]] == 21 : continue  # for testing the effect of gluon jets
			if jetinds[i]==-1: continue
#?			if not T.PFJetPileupMVApassesMediumAK4CHS[jetinds[i]] : continue
			if i==jet1index or i==jet2index: continue
			for j in range(i+1,len(jets)) :
				#if T.PFJetPartonFlavourAK4CHS[jetinds[j]] == 21 : continue  # for testing the effect of gluon jets
				if jetinds[j]==-1: continue
#?				if not T.PFJetPileupMVApassesMediumAK4CHS[jetinds[j]] : continue
				if j==jet1index or j==jet2index: continue
				if i>=j: continue
				#if v == '' : print ' debug : index i', jetinds[i], 'index j', jetinds[j],'m_bb',(jets[i]+jets[j]).M(), ' diff', abs((jets[i]+jets[j]).M()-125), 'dR', abs(jets[i].DeltaR(jets[j]))
				if abs((jets[i]+jets[j]).M()-125) < closestH and (jets[i]+jets[j]).M() > 0 :
					closestH = abs((jets[i]+jets[j]).M()-125)
					if btagScoresMVA[i] > btagScoresMVA[j]:
						highBtagCounter,secondBtagCounter = i,j
						bjet1, bjet2 = jets[i], jets[j]
						indRecoBJet1, indRecoBJet2 = jetinds[i], jetinds[j]
						regr_corrF1, regr_corrF2 = bTagRegSFs[i], bTagRegSFs[j]
						highBtag, secondBtag = btagScoresMVA[i],btagScoresMVA[j]
						highBtagCSV, secondBtagCSV = btagScoresCSV[i],btagScoresCSV[j]
						Hjet1BtagSFL=bTagSFloose[i]
						Hjet1BtagSFM=bTagSFmed[i]
						Hjet2BtagSFL=bTagSFloose[j]
						Hjet2BtagSFM=bTagSFmed[j]
						Hjet1BtagSFL_csv=bTagSFloose_csv[i]
						Hjet1BtagSFM_csv=bTagSFmed_csv[i]
						Hjet2BtagSFL_csv=bTagSFloose_csv[j]
						Hjet2BtagSFM_csv=bTagSFmed_csv[j]
					else:
						highBtagCounter,secondBtagCounter = j,i
						bjet1, bjet2 = jets[j], jets[i]
						indRecoBJet1, indRecoBJet2 = jetinds[j], jetinds[i]
						regr_corrF1, regr_corrF2 = bTagRegSFs[j], bTagRegSFs[i]
						highBtag, secondBtag = btagScoresMVA[j],btagScoresMVA[i]
						highBtagCSV, secondBtagCSV = btagScoresCSV[j],btagScoresCSV[i]
						Hjet1BtagSFL=bTagSFloose[j]
						Hjet1BtagSFM=bTagSFmed[j]
						Hjet2BtagSFL=bTagSFloose[i]
						Hjet2BtagSFM=bTagSFmed[i]
						Hjet1BtagSFL_csv=bTagSFloose_csv[j]
						Hjet1BtagSFM_csv=bTagSFmed_csv[j]
						Hjet2BtagSFL_csv=bTagSFloose_csv[i]
						Hjet2BtagSFM_csv=bTagSFmed_csv[i]
					gotBs = True

	if not gotBs :
		highBtagCSV,highBtag = -20.0,-20.0
		secondBtagCSV,secondBtag = -20.0,-20.0
		highBtagCounter = -1
		secondBtagCounter = -1
		indRecoBJet1 = -1
		indRecoBJet2 = -1
		Hjet1BtagSFL,Hjet1BtagSFM=[1.,1.,1.],[1.,1.,1.]
		Hjet2BtagSFL,Hjet2BtagSFM=[1.,1.,1.],[1.,1.,1.]
		Hjet1BtagSFL_csv,Hjet1BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]
		Hjet2BtagSFL_csv,Hjet2BtagSFM_csv=[1.,1.,1.],[1.,1.,1.]

		for i in range(len(btagScoresMVA)) :
			#if T.PFJetPartonFlavourAK4CHS[jetinds[i]] == 21 : continue  # for testing the effect of gluon jets
			if i==jet1index or i==jet2index: continue
			if btagScoresMVA[i]>highBtag:
				highBtag = btagScoresMVA[i]
				highBtagCSV = btagScoresCSV[i]
				highBtagCounter = i
		for i in range(len(btagScoresMVA)) :
			#if T.PFJetPartonFlavourAK4CHS[jetinds[i]] == 21 : continue  # for testing the effect of gluon jets
			if i==jet1index or i==jet2index: continue
			if i==highBtagCounter: continue
			if btagScoresMVA[i]>secondBtag :
				secondBtag = btagScoresMVA[i]
				secondBtagCSV = btagScoresCSV[i]
				secondBtagCounter = i
		if highBtagCounter >= 0 :
			bjet1,indRecoBJet1 = jets[highBtagCounter],jetinds[highBtagCounter]
			regr_corrF1 = bTagRegSFs[highBtagCounter]
			highBtag,highBtagCSV  = btagScoresMVA[highBtagCounter],btagScoresCSV[highBtagCounter]
			Hjet1BtagSFL=bTagSFloose[highBtagCounter]
			Hjet1BtagSFM=bTagSFmed[highBtagCounter]
			Hjet1BtagSFL_csv=bTagSFloose_csv[highBtagCounter]
			Hjet1BtagSFM_csv=bTagSFmed_csv[highBtagCounter]
		if secondBtagCounter >= 0 :
			bjet2,indRecoBJet2 = jets[secondBtagCounter],jetinds[secondBtagCounter]
			regr_corrF2 = bTagRegSFs[secondBtagCounter]
			secondBtag,secondBtagCSV = btagScoresMVA[secondBtagCounter],btagScoresCSV[secondBtagCounter]
			Hjet2BtagSFL=bTagSFloose[secondBtagCounter]
			Hjet2BtagSFM=bTagSFmed[secondBtagCounter]
			Hjet2BtagSFL_csv=bTagSFloose_csv[secondBtagCounter]
			Hjet2BtagSFM_csv=bTagSFmed_csv[secondBtagCounter]
		gotBs = True #  if cannot really find Hjets, just return EmptyVector

	if not gotZjs :
		## --- Next looking for Z_jj
		closestZ = 2200.
		for i in range(len(jets)-1) :
			if i==highBtagCounter or i==secondBtagCounter: continue
			for j in range(i+1,len(jets)) :
				if j==highBtagCounter or j==secondBtagCounter: continue
				if i>=j: continue
				#if v == '': print 'i:',i,'j:',j,'M_H_mumujj',(lepton1+lepton2+jets[i]+jets[j]).M()
				if abs((lepton1+lepton2+jets[i]+jets[j]).M()-125) < closestZ and (lepton1+lepton2+jets[i]+jets[j]).M() > 0 :
					closestZ = abs((lepton1+lepton2+jets[i]+jets[j]).M()-125)
					jet1index,jet2index = i,j
					jet1, jet2 = jets[i], jets[j]
					indRecoJet1, indRecoJet2 = jetinds[i], jetinds[j]
					jet1CMVA, jet2CMVA = btagScoresMVA[i], btagScoresMVA[j]
					jet1CISV, jet2CISV = btagScoresCSV[i], btagScoresCSV[j]
					Zjet1BtagSFL=bTagSFloose[i]
					Zjet1BtagSFM=bTagSFmed[i]
					Zjet2BtagSFL=bTagSFloose[j]
					Zjet2BtagSFM=bTagSFmed[j]
					Zjet1BtagSFL_csv=bTagSFloose_csv[i]
					Zjet1BtagSFM_csv=bTagSFmed_csv[i]
					Zjet2BtagSFL_csv=bTagSFloose_csv[j]
					Zjet2BtagSFM_csv=bTagSFmed_csv[j]
					gotZjs = True
		#if v == '': print 'Zjet reco ind',indRecoJet1,indRecoJet2,'jets ind',jet1index,jet2index,'M_H_mumujj',(lepton1+lepton2+jets[jet1index]+jets[jet2index]).M()

	if not gotZjs :
		for i in range(len(jets)):
			if i==highBtagCounter or i==secondBtagCounter: continue
			jet1=jets[i]
			indRecoJet1=jetinds[i]
			jet1index = i
			jet1CMVA=btagScoresMVA[i]
			jet1CISV=btagScoresCSV[i]
			Zjet1BtagSFL=bTagSFloose[i]
			Zjet1BtagSFM=bTagSFmed[i]
			Zjet1BtagSFL_csv=bTagSFloose_csv[i]
			Zjet1BtagSFM_csv=bTagSFmed_csv[i]
			break
		for i in range(len(jets)):
			if i==highBtagCounter or i==secondBtagCounter: continue
			if i==jet1index: continue
			jet2=jets[i]
			indRecoJet2=jetinds[i]
			jet2index = i
			jet2CMVA=btagScoresMVA[i]
			jet2CISV=btagScoresCSV[i]
			Zjet2BtagSFL=bTagSFloose[i]
			Zjet2BtagSFM=bTagSFmed[i]
			Zjet2BtagSFL_csv=bTagSFloose_csv[i]
			Zjet2BtagSFM_csv=bTagSFmed_csv[i]
			break
		for i in range(len(jets)):
			if i==highBtagCounter or i==secondBtagCounter: continue
			if i==jet1index or i==jet2index: continue
			jet3=jets[i]
			indRecoJet3=jetinds[i]
			break
		gotZjs = True
	#if v == '': print 'Zjet reco ind',indRecoJet1,indRecoJet2,'jets ind',jet1index,jet2index,'M_H_mumujj',(lepton1+lepton2+jet1+jet2).M()
	#if v == '' :
	#	print 'pts:',bjet1.Pt(),bjet2.Pt(),jet1.Pt(),jet2.Pt()
	#	print 'btag scores:', highBtag,secondBtag,jet1Btag,jet2Btag

	regr_bjet1 = TLorentzVector()
	regr_bjet2 = TLorentzVector()

	regr_bjet1.SetPtEtaPhiE(regr_corrF1*bjet1.Pt(), bjet1.Eta(), bjet1.Phi(), regr_corrF1*bjet1.Energy())
	regr_bjet2.SetPtEtaPhiE(regr_corrF2*bjet2.Pt(), bjet2.Eta(), bjet2.Phi(), regr_corrF2*bjet2.Energy())
	#if v == '' : print ' regr_corrF1 ', regr_corrF1, ' regr_corrF2 ', regr_corrF2
	return [bjet1,highBtagCSV,highBtag,bjet2,secondBtagCSV,secondBtag,jet1,jet2,jet3,jet1CISV,jet2CISV,jet1CMVA,jet2CMVA,indRecoBJet1,indRecoBJet2,indRecoJet1,indRecoJet2,indRecoJet3,regr_bjet1,regr_bjet2,Hjet1BtagSFL,Hjet1BtagSFM,Hjet2BtagSFL,Hjet2BtagSFM,Zjet1BtagSFL,Zjet1BtagSFM,Zjet2BtagSFL,Zjet2BtagSFM,Hjet1BtagSFL_csv,Hjet1BtagSFM_csv,Hjet2BtagSFL_csv,Hjet2BtagSFM_csv,Zjet1BtagSFL_csv,Zjet1BtagSFM_csv,Zjet2BtagSFL_csv,Zjet2BtagSFM_csv]

#def bjetRegressionCorrectionFactor(RegressionReader, _regrvarsnames, bjet, ind_orig, T, met):
#	# see https://github.com/ResonantHbbHgg/bbggTools/blob/master/src/bbggJetRegression.cc#L229
#	if ind_orig==-1: return 1.0 #Case where there are no jets in the event
#	_regrvarsnames['Jet_pt'][0]				= bjet.Pt()
#	_regrvarsnames['Jet_corr'][0]			= T.JetPtAK4CHS[ind_orig]/T.PFJetPtRawAK4CHS[ind_orig]
#	_regrvarsnames['Jet_eta'][0]			= bjet.Eta()
#	_regrvarsnames['Jet_mt'][0]				= T.PFJetMtAK4CHS[ind_orig]
#	_regrvarsnames['Jet_leadTrackPt'][0]	= T.PFJetLeadTrackPtAK4CHS[ind_orig]
#	_regrvarsnames['Jet_leptonPtRel'][0]	= T.PFJetSoftLepRatioAK4CHS[ind_orig]
#	_regrvarsnames['Jet_leptonPt'][0]		= T.PFJetSoftLepPtAK4CHS[ind_orig]
#	_regrvarsnames['Jet_leptonDeltaR'][0]	= T.PFJetSoftLepDrAK4CHS[ind_orig] # default is 0 ==> ok
#	_regrvarsnames['Jet_totHEF'][0]			= T.PFJetChargedHadronEnergyFractionAK4CHS[ind_orig]+T.PFJetNeutralHadronEnergyFractionAK4CHS[ind_orig]
#	_regrvarsnames['Jet_neEmEF'][0]			= T.PFJetNeutralEmEnergyFractionAK4CHS[ind_orig]
#	_regrvarsnames['Jet_vtxPt'][0]			= math.sqrt(T.PFJetVtxPxAK4CHS[ind_orig]*T.PFJetVtxPxAK4CHS[ind_orig] + T.PFJetVtxPyAK4CHS[ind_orig]*T.PFJetVtxPyAK4CHS[ind_orig])
#	_regrvarsnames['Jet_vtxMass'][0]		= T.PFJetVtxMassAK4CHS[ind_orig]
#	_regrvarsnames['Jet_vtx3dL'][0]			= T.PFJetVtx3DValAK4CHS[ind_orig]
#	_regrvarsnames['Jet_vtxNtrk'][0]		= T.PFJetVtxNtracksAK4CHS[ind_orig]
#	if(T.PFJetVtx3DSigAK4CHS[ind_orig] == 0):
#		_regrvarsnames['Jet_vtx3deL'][0]	= 0
#	else:
#		_regrvarsnames['Jet_vtx3deL'][0]	= T.PFJetVtx3DValAK4CHS[ind_orig]/T.PFJetVtx3DSigAK4CHS[ind_orig]
#	_regrvarsnames['nPVs'][0]				= CountVertices(T)
#	_regrvarsnames['Jet_PFMET'][0]			= T.PFMETType1Cor[0]
#	_regrvarsnames['Jet_METDPhi'][0]		= bjet.DeltaPhi(met) # range from mpi to pi

	# calculate corr factor
#	RegressedValues = RegressionReader.EvaluateRegression("BDTG method")
#	regr_corrF = RegressedValues[0]

#	if v == '' :
#		print ' Calculation of regression corr factor '
#		print ' Jet_pt ', _regrvarsnames['Jet_pt'][0]
#		print ' Jet_corr ', _regrvarsnames['Jet_corr'][0]
#		print ' Jet_eta ', _regrvarsnames['Jet_eta'][0]
#		print ' Jet_mt ', _regrvarsnames['Jet_mt'][0]
#		print ' Jet_leadTrackPt ', _regrvarsnames['Jet_leadTrackPt'][0]
#		print ' Jet_leptonPtRel ', _regrvarsnames['Jet_leptonPtRel'][0]
#		print ' Jet_leptonPt ', _regrvarsnames['Jet_leptonPt'][0]
#		print ' Jet_leptonDeltaR ', _regrvarsnames['Jet_leptonDeltaR'][0]
#		print ' Jet_totHEF ', _regrvarsnames['Jet_totHEF'][0]
#		print ' Jet_neEmEF ', _regrvarsnames['Jet_neEmEF'][0]
#		print ' Jet_vtxPt ', _regrvarsnames['Jet_vtxPt'][0], T.PFJetVtxPxAK4CHS[ind_orig], T.PFJetVtxPyAK4CHS[ind_orig]
#		print ' Jet_vtxMass ', _regrvarsnames['Jet_vtxMass'][0]
#		print ' Jet_vtx3dL ', _regrvarsnames['Jet_vtx3dL'][0]
#		print ' Jet_vtxNtrk ', _regrvarsnames['Jet_vtxNtrk'][0]
#		print ' Jet_vtx3deL ', _regrvarsnames['Jet_vtx3deL'][0]
#		print ' nPVs ', _regrvarsnames['nPVs'][0]
#		print ' Jet_PFMET ', _regrvarsnames['Jet_PFMET'][0]
#		print ' Jet_METDPhi ', _regrvarsnames['Jet_METDPhi'][0]
#		print ' regr_corrF ', regr_corrF
#	return regr_corrF

########################################### New Function for AK8 jet tagging###########################
################## doesn't go through loose id jets first, so this function should get these variables from the Ak8 jets:
#### [jets,jetinds,met,JetFailThreshold,NHFs,NEMFs,CSVscores,bMVAscores,bTagSFsLoose,bTagSFsMed,bTagSFsLoose_csv,bTagSFsMed_csv]
################## Needs to return something similar to GetHHJetsNew, so these variables:
####[bjet1,highBtagCSV,highBtag,bjet2,secondBtagCSV,secondBtag,jet1,jet2,jet3,jet1CISV,jet2CISV,jet1CMVA,jet2CMVA,indRecoBJet1,indRecoBJet2,indRecoJet1,indRecoJet2,indRecoJet3,
#### regr_bjet1,regr_bjet2,Hjet1BtagSFL,Hjet1BtagSFM,Hjet2BtagSFL,Hjet2BtagSFM,Zjet1BtagSFL,Zjet1BtagSFM,Zjet2BtagSFL,Zjet2BtagSFM,Hjet1BtagSFL_csv,Hjet1BtagSFM_csv,Hjet2BtagSFL_csv,Hjet2BtagSFM_csv,
#### Zjet1BtagSFL_csv,Zjet1BtagSFM_csv,Zjet2BtagSFL_csv,Zjet2BtagSFM_csv]
################## AK8 subjets don't have MVA scores, so only using CSV scores
#######################################################################################################


def AK8calculateBDTdiscriminant(reader, classifierTag, _bdtvarnames, T, Pt_muon1, Pt_muon2, Pt_AK8jet1) :
#def calculateBDTdiscriminant(reader, classifierTag, _bdtvarnames, AK8_Pt_jet, AK8_Eta_jet, AK8_Phi_jet, AK8_Mass_jet, AK8_dRuj, AK8_CSV_jet, Pt_muon1, Pt_AK8jet1) :
	emptyvector = TLorentzVector()
	emptyvector.SetPtEtaPhiM(0,0,0,0)

################## Get muons ##################
	muons = []

	for n in range(T.nMuon):
		m = TLorentzVector()
		m.SetPtEtaPhiM(T.Muon_pt[n],T.Muon_eta[n],T.Muon_phi[n],T.Muon_mass[n])
		muons.append(m)
	while len(muons)<2:
		muons.append(emptyvector)
	combinedMuons = muons[0]+muons[1]

################# loop over jets and calculate BDT disciminate for each one ###################
	PFJetPtAK8 = T.FatJet_pt
	PFJetEtaAK8 = T.FatJet_eta
	PFJetPhiAK8 = T.FatJet_phi
	PFJetMassAK8 = T.FatJet_mass
	PFJetCSVAK8 = T.FatJet_btagCSVV2
	jets_AK8 = []

	highestbdtdisc = -1
	bdtdisc = -1
	highestjetind = -1

	for n in range(len(PFJetPtAK8)):
		m = TLorentzVector()
		m.SetPtEtaPhiM(PFJetPtAK8[n],PFJetEtaAK8[n],PFJetPhiAK8[n],PFJetMassAK8[n])
		jets_AK8.append(m)
		dRujAK8=0
		dRujAK8=m.DeltaR(combinedMuons)
		if 'AK8_Mass_Hjet_genMatched'          in _bdtvarnames: _bdtvarnames['AK8_Mass_Hjet_genMatched'][0]          = 0
		if 'AK8_dRujH_genMatched'              in _bdtvarnames: _bdtvarnames['AK8_dRujH_genMatched'][0]	             = dRujAK8
		if 'AK8_Pt_Hjet_genMatched'            in _bdtvarnames: _bdtvarnames['AK8_Pt_Hjet_genMatched'][0]    	     = PFJetPtAK8[n]
		if 'AK8_Eta_Hjet_genMatched'           in _bdtvarnames: _bdtvarnames['AK8_Eta_Hjet_genMatched'][0]           = PFJetEtaAK8[n]
		if 'AK8_Phi_Hjet_genMatched'           in _bdtvarnames: _bdtvarnames['AK8_Phi_Hjet_genMatched'][0]	     = PFJetPhiAK8[n]
		if 'AK8_CSV_Hjet_genMatched'           in _bdtvarnames: _bdtvarnames['AK8_CSV_Hjet_genMatched'][0]	     = PFJetCSVAK8[n]
		if (Pt_muon1>0 and Pt_muon2>0 and PFJetPtAK8[n]>0 and Pt_AK8jet1>0 and PFJetCSVAK8[n]>0) :
			bdtdisc = reader.EvaluateMVA(classifierTag)
		if bdtdisc > highestbdtdisc:
			highestbdtdisc = bdtdisc
			highestjetind = n

	highestbdtdiscZ = -1
	bdtdiscZ = -1
	highestjetindZ = -1

	for n in range(len(PFJetPtAK8)):
		if n == highestjetind: continue
		m = TLorentzVector()
		m.SetPtEtaPhiM(PFJetPtAK8[n],PFJetEtaAK8[n],PFJetPhiAK8[n],PFJetMassAK8[n])
		dRujAK8=0
		dRujAK8=m.DeltaR(combinedMuons)
		if 'AK8_Mass_Zjet_genMatched'          in _bdtvarnamesZ: _bdtvarnamesZ['AK8_Mass_Zjet_genMatched'][0]        = 0
		if 'AK8_dRujZ_genMatched'              in _bdtvarnamesZ: _bdtvarnamesZ['AK8_dRujZ_genMatched'][0]	     = dRujAK8
		if 'AK8_Pt_Zjet_genMatched'            in _bdtvarnamesZ: _bdtvarnamesZ['AK8_Pt_Zjet_genMatched'][0]    	     = PFJetPtAK8[n]
		if 'AK8_Eta_Zjet_genMatched'           in _bdtvarnamesZ: _bdtvarnamesZ['AK8_Eta_Zjet_genMatched'][0]         = PFJetEtaAK8[n]
		if 'AK8_Phi_Zjet_genMatched'           in _bdtvarnamesZ: _bdtvarnamesZ['AK8_Phi_Zjet_genMatched'][0]	     = PFJetPhiAK8[n]
		if 'AK8_CSV_Zjet_genMatched'           in _bdtvarnamesZ: _bdtvarnamesZ['AK8_CSV_Zjet_genMatched'][0]	     = PFJetCSVAK8[n]
		if (Pt_muon1>0 and Pt_muon2>0 and PFJetPtAK8[n]>0 and Pt_AK8jet1>0 and PFJetCSVAK8[n]>0) :
			bdtdiscZ = readerZ.EvaluateMVA(classifierTag)

		if bdtdiscZ > highestbdtdiscZ:
			highestbdtdiscZ = bdtdiscZ
			highestjetindZ = n

	if highestjetind == -1:
		bdtAK8Hjet = emptyvector
	else:
		bdtAK8Hjet = jets_AK8[highestjetind]
	if highestjetindZ == -1:
		bdtAK8Zjet = emptyvector
	else:
		bdtAK8Zjet = jets_AK8[highestjetindZ]
	return (bdtAK8Hjet, bdtAK8Zjet, highestbdtdisc, highestbdtdiscZ, highestjetind, highestjetindZ)

def calculateBDTdiscriminant(reader, classifierTag, _bdtvarnames, _Mll4j, _Mbb_H, _Mjj_Z, _Mll, _Mlljj, _ptlep1, _ptlep2, _ptmet, _Pt_Hjet1, _Pt_Hjet2, _Pt_Zjet1, _Pt_Zjet2, _Pt_ll, _Pt_Hjets, _Pt_Zjets, _dRbb_H, _dRjj_Z, _DRll, _phi0_ll, _phi1_ll, _phi0_zz_ll, _phi1_zll, _phi1_zjj_ll, bscoreMVA1, bscoreMVA2, _dRl1Hj1, _dRl1Hj2, _dRl2Hj1, _dRl2Hj2, _dRl1Zj1, _dRl1Zj2, _dRl2Zj1, _dRl2Zj2, _dRllbb_H, _dRlljj_Z, _cosThetaStarLep, _cosTheta_hbb_ll, _cosTheta_zll_hzz, _cosThetaStar_ll, _cosThetaStarZll_CS, _cosTheta_Zll, _etalep1, _etalep2, _philep1, _philep2, _DPHIlv, _dPHIlljj_Z, _dPHIllbb_H, _dPhibb_H, _dPhijj_Z) :

	if 'M_uu4j'                in _bdtvarnames: _bdtvarnames['M_uu4j'][0]                = _Mll4j
	if 'Mbb_H'                 in _bdtvarnames: _bdtvarnames['Mbb_H'][0]			     = _Mbb_H
	if 'Mjj_Z'                 in _bdtvarnames: _bdtvarnames['Mjj_Z'][0]    		     = _Mjj_Z
	if 'M_uu'                  in _bdtvarnames: _bdtvarnames['M_uu'][0]      		     = _Mll
	if 'M_uujj'                in _bdtvarnames: _bdtvarnames['M_uujj'][0]	             = _Mlljj

	if 'Pt_muon1'              in _bdtvarnames: _bdtvarnames['Pt_muon1'][0]	       		 = _ptlep1
	if 'Pt_muon2'              in _bdtvarnames: _bdtvarnames['Pt_muon2'][0]  			 = _ptlep2
	if 'Pt_miss'               in _bdtvarnames: _bdtvarnames['Pt_miss'][0]               = _ptmet
	if 'Pt_Hjet1'              in _bdtvarnames: _bdtvarnames['Pt_Hjet1'][0]              = _Pt_Hjet1
	if 'Pt_Hjet2'              in _bdtvarnames: _bdtvarnames['Pt_Hjet2'][0]              = _Pt_Hjet2
	if 'Pt_Zjet1'              in _bdtvarnames: _bdtvarnames['Pt_Zjet1'][0]              = _Pt_Zjet1
	if 'Pt_Zjet2'              in _bdtvarnames: _bdtvarnames['Pt_Zjet2'][0]              = _Pt_Zjet2

	if 'Pt_uu'                 in _bdtvarnames: _bdtvarnames['Pt_uu'][0]                 = _Pt_ll
	if 'Pt_Hjets'              in _bdtvarnames: _bdtvarnames['Pt_Hjets'][0]              = _Pt_Hjets
	if 'Pt_Zjets'              in _bdtvarnames: _bdtvarnames['Pt_Zjets'][0]              = _Pt_Zjets

	if 'DR_bb_H'               in _bdtvarnames: _bdtvarnames['DR_bb_H'][0]		       	 = _dRbb_H
	if 'DR_jj_Z'               in _bdtvarnames: _bdtvarnames['DR_jj_Z'][0]	       		 = _dRjj_Z
	if 'DR_muon1muon2'         in _bdtvarnames: _bdtvarnames['DR_muon1muon2'][0]	     = _DRll

	if 'abs(phi0_uu)'          in _bdtvarnames: _bdtvarnames['abs(phi0_uu)'][0]		     = math.fabs(_phi0_ll)
	if 'abs(phi1_uu)'		   in _bdtvarnames: _bdtvarnames['abs(phi1_uu)'][0]			 = math.fabs(_phi1_ll)
	if 'abs(phi0_zz_uu)'	   in _bdtvarnames: _bdtvarnames['abs(phi0_zz_uu)'][0]	     = math.fabs(_phi0_zz_ll)
	if 'abs(phi1_zuu)'         in _bdtvarnames: _bdtvarnames['abs(phi1_zuu)'][0]         = math.fabs(_phi1_zll)
	if 'abs(phi1_zjj_uu)'      in _bdtvarnames: _bdtvarnames['abs(phi1_zjj_uu)'][0]      = math.fabs(_phi1_zjj_ll)

	if 'CMVA_bjet1'            in _bdtvarnames: _bdtvarnames['CMVA_bjet1'][0]			 = bscoreMVA1
	if 'CMVA_bjet2'            in _bdtvarnames: _bdtvarnames['CMVA_bjet2'][0]	         = bscoreMVA2

	if 'DR_u1Hj1'              in _bdtvarnames: _bdtvarnames['DR_u1Hj1'][0]              = _dRl1Hj1
	if 'DR_u1Hj2'              in _bdtvarnames: _bdtvarnames['DR_u1Hj2'][0]              = _dRl1Hj2
	if 'DR_u2Hj1'              in _bdtvarnames: _bdtvarnames['DR_u2Hj1'][0]              = _dRl2Hj1
	if 'DR_u2Hj2'              in _bdtvarnames: _bdtvarnames['DR_u2Hj2'][0]              = _dRl2Hj2
	if 'DR_u1Zj1'              in _bdtvarnames: _bdtvarnames['DR_u1Zj1'][0]              = _dRl1Zj1
	if 'DR_u1Zj2'              in _bdtvarnames: _bdtvarnames['DR_u1Zj2'][0]              = _dRl1Zj2
	if 'DR_u2Zj1'              in _bdtvarnames: _bdtvarnames['DR_u2Zj1'][0]              = _dRl2Zj1
	if 'DR_u2Zj2'              in _bdtvarnames: _bdtvarnames['DR_u2Zj2'][0]              = _dRl2Zj2

	if 'DR_uu_bb_H'            in _bdtvarnames: _bdtvarnames['DR_uu_bb_H'][0]		     = _dRllbb_H
	if 'DR_uu_jj_Z'            in _bdtvarnames: _bdtvarnames['DR_uu_jj_Z'][0]            = _dRlljj_Z

	if 'abs(cosThetaStarMu)'     in _bdtvarnames: _bdtvarnames['abs(cosThetaStarMu)'][0]	 = math.fabs(_cosThetaStarLep)
	if 'abs(cosTheta_hbb_uu)'    in _bdtvarnames: _bdtvarnames['abs(cosTheta_hbb_uu)'][0]	 = math.fabs(_cosTheta_hbb_ll)
	if 'abs(cosTheta_zuu_hzz)'   in _bdtvarnames: _bdtvarnames['abs(cosTheta_zuu_hzz)'][0]   = math.fabs(_cosTheta_zll_hzz)
	if 'abs(cosThetaStar_uu)'    in _bdtvarnames: _bdtvarnames['abs(cosThetaStar_uu)'][0]    = math.fabs(_cosThetaStar_ll)
	if 'abs(cosThetaStarZuu_CS)' in _bdtvarnames: _bdtvarnames['abs(cosThetaStarZuu_CS)'][0] = math.fabs(_cosThetaStarZll_CS)
	if 'abs(cosTheta_Zuu)'       in _bdtvarnames: _bdtvarnames['abs(cosTheta_Zuu)'][0]       = math.fabs(_cosTheta_Zll)

	if 'abs(Eta_muon1)'		   in _bdtvarnames: _bdtvarnames['abs(Eta_muon1)'][0]        = math.fabs(_etalep1)
	if 'abs(Eta_muon2)'		   in _bdtvarnames: _bdtvarnames['abs(Eta_muon2)'][0]        = math.fabs(_etalep2)
	if 'abs(Phi_muon1)'		   in _bdtvarnames: _bdtvarnames['abs(Phi_muon1)'][0]        = math.fabs(_philep1)
	if 'abs(Phi_muon2)'		   in _bdtvarnames: _bdtvarnames['abs(Phi_muon2)'][0]        = math.fabs(_philep2)
	if 'abs(DPhi_muon1met)'	   in _bdtvarnames: _bdtvarnames['abs(DPhi_muon1met)'][0]    = math.fabs(_DPHIlv)
	if 'abs(DPhi_uu_jj_Z)'	   in _bdtvarnames: _bdtvarnames['abs(DPhi_uu_jj_Z)'][0]     = math.fabs(_dPHIlljj_Z)
	if 'abs(DPhi_uu_bb_H)'	   in _bdtvarnames: _bdtvarnames['abs(DPhi_uu_bb_H)'][0]     = math.fabs(_dPHIllbb_H)
	if 'abs(DPhi_bb_H)'		   in _bdtvarnames: _bdtvarnames['abs(DPhi_bb_H)'][0]        = math.fabs(_dPhibb_H)
	if 'abs(DPhi_jj_Z)'	       in _bdtvarnames: _bdtvarnames['abs(DPhi_jj_Z)'][0]        = math.fabs(_dPhijj_Z)

	#--- electron variables
	if 'M_ee4j'                in _bdtvarnames: _bdtvarnames['M_ee4j'][0]                = _Mll4j
	if 'M_ee'                  in _bdtvarnames: _bdtvarnames['M_ee'][0]      		     = _Mll
	if 'M_eejj'                in _bdtvarnames: _bdtvarnames['M_eejj'][0]	             = _Mlljj
	if 'Pt_ele1'               in _bdtvarnames: _bdtvarnames['Pt_ele1'][0]	       		 = _ptlep1
	if 'Pt_ele2'               in _bdtvarnames: _bdtvarnames['Pt_ele2'][0]  			 = _ptlep2
	if 'Pt_ee'                 in _bdtvarnames: _bdtvarnames['Pt_ee'][0]                 = _Pt_ll
	if 'DR_ele1ele2'           in _bdtvarnames: _bdtvarnames['DR_ele1ele2'][0]	         = _DRll

	if 'abs(phi0_ee)'          in _bdtvarnames: _bdtvarnames['abs(phi0_ee)'][0]		     = math.fabs(_phi0_ll)
	if 'abs(phi1_ee)'		   in _bdtvarnames: _bdtvarnames['abs(phi1_ee)'][0]			 = math.fabs(_phi1_ll)
	if 'abs(phi0_zz_ee)'	   in _bdtvarnames: _bdtvarnames['abs(phi0_zz_ee)'][0]	     = math.fabs(_phi0_zz_ll)
	if 'abs(phi1_zee)'         in _bdtvarnames: _bdtvarnames['abs(phi1_zee)'][0]         = math.fabs(_phi1_zll)
	if 'abs(phi1_zjj_ee)'      in _bdtvarnames: _bdtvarnames['abs(phi1_zjj_ee)'][0]      = math.fabs(_phi1_zjj_ll)

	if 'DR_e1Hj1'              in _bdtvarnames: _bdtvarnames['DR_e1Hj1'][0]              = _dRl1Hj1
	if 'DR_e1Hj2'              in _bdtvarnames: _bdtvarnames['DR_e1Hj2'][0]              = _dRl1Hj2
	if 'DR_e2Hj1'              in _bdtvarnames: _bdtvarnames['DR_e2Hj1'][0]              = _dRl2Hj1
	if 'DR_e2Hj2'              in _bdtvarnames: _bdtvarnames['DR_e2Hj2'][0]              = _dRl2Hj2
	if 'DR_e1Zj1'              in _bdtvarnames: _bdtvarnames['DR_e1Zj1'][0]              = _dRl1Zj1
	if 'DR_e1Zj2'              in _bdtvarnames: _bdtvarnames['DR_e1Zj2'][0]              = _dRl1Zj2
	if 'DR_e2Zj1'              in _bdtvarnames: _bdtvarnames['DR_e2Zj1'][0]              = _dRl2Zj1
	if 'DR_e2Zj2'              in _bdtvarnames: _bdtvarnames['DR_e2Zj2'][0]              = _dRl2Zj2

	if 'DR_ee_bb_H'            in _bdtvarnames: _bdtvarnames['DR_ee_bb_H'][0]		     = _dRllbb_H
	if 'DR_ee_jj_Z'            in _bdtvarnames: _bdtvarnames['DR_ee_jj_Z'][0]            = _dRlljj_Z

	if 'abs(cosThetaStarEle)'    in _bdtvarnames: _bdtvarnames['abs(cosThetaStarEle)'][0]	 = math.fabs(_cosThetaStarLep)
	if 'abs(cosTheta_hbb_ee)'    in _bdtvarnames: _bdtvarnames['abs(cosTheta_hbb_ee)'][0]	 = math.fabs(_cosTheta_hbb_ll)
	if 'abs(cosTheta_zee_hzz)'   in _bdtvarnames: _bdtvarnames['abs(cosTheta_zee_hzz)'][0]   = math.fabs(_cosTheta_zll_hzz)
	if 'abs(cosThetaStar_ee)'    in _bdtvarnames: _bdtvarnames['abs(cosThetaStar_ee)'][0]    = math.fabs(_cosThetaStar_ll)
	if 'abs(cosThetaStarZee_CS)' in _bdtvarnames: _bdtvarnames['abs(cosThetaStarZee_CS)'][0] = math.fabs(_cosThetaStarZll_CS)
	if 'abs(cosTheta_Zee)'       in _bdtvarnames: _bdtvarnames['abs(cosTheta_Zee)'][0]       = math.fabs(_cosTheta_Zll)

	if 'abs(Eta_ele1)'		   in _bdtvarnames: _bdtvarnames['abs(Eta_ele1)'][0]        = math.fabs(_etalep1)
	if 'abs(Eta_ele2)'		   in _bdtvarnames: _bdtvarnames['abs(Eta_ele2)'][0]        = math.fabs(_etalep2)
	if 'abs(Phi_ele1)'		   in _bdtvarnames: _bdtvarnames['abs(Phi_ele1)'][0]        = math.fabs(_philep1)
	if 'abs(Phi_ele2)'		   in _bdtvarnames: _bdtvarnames['abs(Phi_ele2)'][0]        = math.fabs(_philep2)
	if 'abs(DPhi_ele1met)'	   in _bdtvarnames: _bdtvarnames['abs(DPhi_ele1met)'][0]    = math.fabs(_DPHIlv)
	if 'abs(DPhi_ee_jj_Z)'	   in _bdtvarnames: _bdtvarnames['abs(DPhi_ee_jj_Z)'][0]     = math.fabs(_dPHIlljj_Z)
	if 'abs(DPhi_ee_bb_H)'	   in _bdtvarnames: _bdtvarnames['abs(DPhi_ee_bb_H)'][0]     = math.fabs(_dPHIllbb_H)

	# calculate BDT disriminator
	out_bdtdisc = -999.
	# preselections
	#Removing preselection requirement....BDT will return -999 for events with non-sensible variables
	#if (_ptmu1 > 20 and _ptmu2 > 10 and _Pt_Hjet1 > 20 and _Pt_Hjet2 > 20 and _Pt_Zjet1 > 20 and _Pt_Zjet2 > 20 and _Muu > 12 and _isMuonEvent and (_qmu1*_qmu2) < 0 and ((bscoreMVA1>-0.5884)+(bscoreMVA2>-0.5884)+(_cmva_Zjet1>-0.5884)+(_cmva_Zjet2>-0.5884)) > 0) :
	##Msig = int(classifierTag.split('_M')[1])
	##if Msig <= 300: MET_cut = 40.0
	##elif Msig <= 600: MET_cut = 75.0
	##else: MET_cut = 100.0
	## MET cut is not needed here, TMVA will calculate bdt score (because MET variable is not used) ?, but we will put the cut in analysis level anyway

	if 'DR_muon1muon2' in _bdtvarnames:
		if (_ptlep1 > 20 and _ptlep2 > 10 and _Pt_Hjet1 > 20 and _Pt_Hjet2 > 20 and _Pt_Zjet1 > 20 and _Pt_Zjet2 > 20 and _Mll > 15) :			out_bdtdisc = reader.EvaluateMVA(classifierTag)
			#print classifierTag,' out_bdtdisc ', out_bdtdisc
	elif 'DR_ele1ele2' in _bdtvarnames:
		if (_ptlep1 > 25 and _ptlep2 > 15 and _Pt_Hjet1 > 20 and _Pt_Hjet2 > 20 and _Pt_Zjet1 > 20 and _Pt_Zjet2 > 20 and _Mll > 15) :			out_bdtdisc = reader.EvaluateMVA(classifierTag)
			#print classifierTag,' out_bdtdisc ', out_bdtdisc
	#if v == '' : print ' out_bdtdisc ', out_bdtdisc
	return out_bdtdisc

def getCosThetaStar_CS(h1, h2, ebeam = 6500.) :
	#cos theta star angle in the Collins Soper frame
	p1, p2, hh = TLorentzVector(), TLorentzVector(), TLorentzVector()
	p1.SetPxPyPzE(0, 0,  ebeam, ebeam)
	p2.SetPxPyPzE(0, 0, -ebeam, ebeam)
	hh = h1 + h2
	boost = TVector3(- hh.BoostVector())
	#boost = - hh.BoostVector();
	p1.Boost(boost)
	p2.Boost(boost)
	h1.Boost(boost)
	#TVector3 CSaxis = p1.Vect().Unit() - p2.Vect().Unit()
	CSaxis = TVector3(p1.Vect().Unit() - p2.Vect().Unit())
	CSaxis.Unit()

	return math.cos(   CSaxis.Angle( h1.Vect().Unit() )    )

def HelicityCosTheta(Booster, Boosted) :
	BoostVector = TVector3( Booster.BoostVector() )
	Boosted.Boost( -BoostVector.x(), -BoostVector.y(), -BoostVector.z() )
	return Boosted.CosTheta()

def CosThetaAngles(Hj1, Hj2, Zj1, Zj2, ell1, ell2) :
	bb, zz, diHiggsCandidate = TLorentzVector(), TLorentzVector(), TLorentzVector()
	zz = Zj1 + Zj2 + ell1 + ell2
	bb = Hj1 + Hj2
	diHiggsCandidate = Hj1 + Hj2 + Zj1 + Zj2 + ell1 + ell2

	helicityThetas = []
	BoostedHgg, HHforBoost = TLorentzVector(), TLorentzVector()
	HHforBoost.SetPtEtaPhiE(diHiggsCandidate.Pt(), diHiggsCandidate.Eta(), diHiggsCandidate.Phi(), diHiggsCandidate.Energy())
	BoostedHgg.SetPtEtaPhiE(zz.Pt(), zz.Eta(), zz.Phi(), zz.Energy())
	helicityThetas.append( HelicityCosTheta(HHforBoost, BoostedHgg) ) # CosThetaStar

	BoostedLeadingJet, HbbforBoost = TLorentzVector(), TLorentzVector()
	HbbforBoost.SetPtEtaPhiE(bb.Pt(), bb.Eta(), bb.Phi(), bb.Energy())
	if (Hj1.Pt() >= Hj2.Pt()) : # is this leading jet ?
		BoostedLeadingJet.SetPtEtaPhiE(Hj1.Pt(), Hj1.Eta(), Hj1.Phi(), Hj1.Energy())
	else :
		BoostedLeadingJet.SetPtEtaPhiE(Hj2.Pt(), Hj2.Eta(), Hj2.Phi(), Hj2.Energy())
	helicityThetas.append( HelicityCosTheta(HbbforBoost, BoostedLeadingJet) ) # CosTheta_hbb


	BoostedZjj, BoostedZuu, BoostedLeadingZj, BoostedLeadingZu, HzzforBoost = TLorentzVector(), TLorentzVector(), TLorentzVector(), TLorentzVector(), TLorentzVector()
	HzzforBoost.SetPtEtaPhiE(zz.Pt(), zz.Eta(), zz.Phi(), zz.Energy())

	BoostedZjj.SetPtEtaPhiE((Zj1+Zj2).Pt(), (Zj1+Zj2).Eta(), (Zj1+Zj2).Phi(), (Zj1+Zj2).Energy())
	#if v == '': print 'before:', BoostedZjj.Pt(), BoostedZjj.Eta()
	helicityThetas.append( HelicityCosTheta(HzzforBoost, BoostedZjj) ) # CosTheta_zjj_hzz
	#if v == '': print 'after :', BoostedZjj.Pt(), BoostedZjj.Eta()

	BoostedZuu.SetPtEtaPhiE((ell1 + ell2).Pt(), (ell1 + ell2).Eta(), (ell1 + ell2).Phi(), (ell1 + ell2).Energy())
	helicityThetas.append( HelicityCosTheta(HzzforBoost, BoostedZuu) ) # CosTheta_zuu_hzz

	BoostedLeadingZj.SetPtEtaPhiE(Zj1.Pt(), Zj1.Eta(), Zj1.Phi(), Zj1.Energy())
	helicityThetas.append( HelicityCosTheta(HzzforBoost, BoostedLeadingZj) ) # CosTheta_zj1_hzz
	#if v == '': print 'CosTheta_zz:', helicityThetas[2], 'CosTheta_zz_test', helicityThetas[3]

	BoostedLeadingZu.SetPtEtaPhiE(ell1.Pt(), ell1.Eta(), ell1.Phi(), ell1.Energy())
	helicityThetas.append( HelicityCosTheta(HzzforBoost, BoostedLeadingZu) ) # CosTheta_zu1_hzz

	return helicityThetas

def CosThetaAngles_ZZ(Zj1, Zj2, ell1, ell2) :
	zz = TLorentzVector()
	zz = Zj1 + Zj2 + ell1 + ell2
	zjj = Zj1 + Zj2
	zellell = ell1 + ell2

	helicityThetas = []

	ZZforBoost, BoostedZuu, BoostedZjj = TLorentzVector(), TLorentzVector(), TLorentzVector()
	ZZforBoost.SetPtEtaPhiE(zz.Pt(), zz.Eta(), zz.Phi(), zz.Energy())

	BoostedZuu.SetPtEtaPhiE(zellell.Pt(), zellell.Eta(), zellell.Phi(), zellell.Energy())
	helicityThetas.append( HelicityCosTheta(ZZforBoost, BoostedZuu) ) # CosThetaStar_Zuu

	BoostedZjj.SetPtEtaPhiE(zjj.Pt(), zjj.Eta(), zjj.Phi(), zjj.Energy())
	helicityThetas.append( HelicityCosTheta(ZZforBoost, BoostedZjj) ) # CosThetaStar_Zjj

	return helicityThetas

def norm_planes_hi(partons, dihiggs) :
	boost_H = TVector3( - dihiggs.BoostVector() )

	partons3v = []
	for i in range(len(partons)) :
		partons_i_boosted = TLorentzVector()
		partons_i_boosted = partons[i]
		partons_i_boosted.Boost(boost_H)
		partons3v.append( partons_i_boosted.Vect().Unit() )

	vnorm = []
	R = TRandom()
	for i in range(2) :
		rndm = R.Uniform(1)
		#if v == '': print 'i:', i, 'rndm', rndm
		if (rndm > 0.5) :
			vnorm.append( (partons3v[i*2].Cross(partons3v[i*2+1])).Unit() )
		else :
			vnorm.append( -1*(partons3v[i*2].Cross(partons3v[i*2+1])).Unit() )

	return vnorm

def getPhi(Hj1, Hj2, Zj1, Zj2, ell1, ell2) :
	vPhi = []
	if (Hj1.Pt()<=0. or Hj2.Pt()<=0. or Zj1.Pt()<=0. or Zj2.Pt()<=0. or ell1.Pt()<=0. or ell2.Pt()<=0.) :
		vPhi.append(-3.5)
		vPhi.append(-3.5)
	else :
		zz, diHiggsCandidate = TLorentzVector(), TLorentzVector()
		zz = Zj1 + Zj2 + ell1 + ell2
		diHiggsCandidate = Hj1 + Hj2 + Zj1 + Zj2 + ell1 + ell2

		partons = []
		partons.append(Zj1 + Zj2) #leadingLepton
		partons.append(ell1 + ell2) #subleadingLepton
		partons.append(Hj1) #leadingJet
		partons.append(Hj2) #subleadingJet

		# Define hzz direction
		hzz = TLorentzVector()
		hzz = Zj1 + Zj2 + ell1 + ell2

		boost_H = TVector3( - diHiggsCandidate.BoostVector() )
		hzz.Boost(boost_H);

		hzz_vect = TVector3( hzz.Vect().Unit() ) # hzz_vect has been boosted
		#hzz_vect_nobst = TVector3( zz.Vect().Unit() ) # hzz_vect_nobst has not been boosted

		#if v == '': print 'hzz_vect       :', hzz_vect.Pt(), hzz_vect.Eta(), hzz_vect.Phi()
		#if v == '': print 'hzz_vect_nobst :', hzz_vect_nobst.Pt(), hzz_vect_nobst.Eta(), hzz_vect_nobst.Phi()

		# Calculate the normal to Hzz and hbb decay plane
		vnorm = norm_planes_hi(partons, diHiggsCandidate)

		# Calculate Phi
		dsignhgg = hzz_vect.Dot(vnorm[1].Cross(vnorm[0]))/(abs(hzz_vect.Dot(vnorm[1].Cross(vnorm[0])))) # hzz_vect here is not important
		vPhi.append( dsignhgg*(-1) * math.acos(vnorm[0].Dot(vnorm[1])) )

		# Define z direction
		p1 = TLorentzVector()
		p1.SetPxPyPzE(0, 0,  6500, 6500)
		z_vect = TVector3( p1.Vect().Unit() )

		# Calcuate the normal to Hzz and z-direction plane
		zzprime = TVector3((z_vect.Cross(hzz_vect)).Unit())
		#zzprime = TVector3((z_vect.Cross(hzz_vect_nobst)).Unit())

		# Calculate Phi1
		dsignhgg2 = hzz_vect.Dot(zzprime.Cross(vnorm[0]))/(abs(hzz_vect.Dot(zzprime.Cross(vnorm[0]))))  # hzz_vect here is not important
		if -1<=zzprime.Dot(vnorm[0]) and zzprime.Dot(vnorm[0])<=1:
			vPhi.append( dsignhgg2 * math.acos(zzprime.Dot(vnorm[0])) )
		else :
			vPhi.append(-3.5)

	return vPhi

def getPhi_ZZ(Zj1, Zj2, ell1, ell2) :
	vPhi = []
	if (Zj1.Pt()<=0. or Zj2.Pt()<=0. or ell1.Pt()<=0. or ell2.Pt()<=0.) :
		vPhi.append(-3.5)
		vPhi.append(-3.5)
		vPhi.append(-3.5)
	else :
		zz = TLorentzVector()
		zz = Zj1 + Zj2 + ell1 + ell2

		partons = []
		partons.append(ell1) #leadingLepton
		partons.append(ell2) #subleadingLepton
		partons.append(Zj1) #leadingJet
		partons.append(Zj2) #subleadingJet

		# Define Zuu direction
		zuu = TLorentzVector()
		zuu = ell1 + ell2

		boost_ZZ = TVector3( - zz.BoostVector() )
		zuu.Boost(boost_ZZ);
		zuu_vect = TVector3( zuu.Vect().Unit() ) # zuu_vect has been boosted

		# Calculate the normal to Zuu and Zjj decay plane
		vnorm = norm_planes_hi(partons, zz)

		# Calculate Phi
                #fixme Morse division by zero very small amount of the time
		if abs(zuu_vect.Dot(vnorm[1].Cross(vnorm[0])))>0:
			dsignhgg = zuu_vect.Dot(vnorm[1].Cross(vnorm[0]))/(abs(zuu_vect.Dot(vnorm[1].Cross(vnorm[0])))) # zuu_vect here is NOT important
		else:
			dsignhgg = 0
                if -1<=vnorm[0].Dot(vnorm[1]) and vnorm[0].Dot(vnorm[1])<=1:
                        vPhi.append( dsignhgg*(-1) * math.acos(vnorm[0].Dot(vnorm[1])) )
                else:
                        vPhi.append(-3.5)

		# Define z direction
		p1 = TLorentzVector()
		p1.SetPxPyPzE(0, 0,  6500, 6500)
		z_vect = TVector3( p1.Vect().Unit() )

		# Calcuate the normal to Zuu and z-direction plane
		zz1prime = TVector3((z_vect.Cross(zuu_vect)).Unit())  # zuu_vect here IS important

		# Calculate Phi1_zuu
                #fixme Morse division by zero very small amount of the time
		if abs(zuu_vect.Dot(zz1prime.Cross(vnorm[0])))>0:
			dsignhgg2 = zuu_vect.Dot(zz1prime.Cross(vnorm[0]))/(abs(zuu_vect.Dot(zz1prime.Cross(vnorm[0]))))  # zuu_vect here is NOT important
		else:
			dsignhgg2 = 0
		#print dsignhgg2,zz1prime.Dot(vnorm[0])
		vPhi.append( dsignhgg2 * math.acos(round(zz1prime.Dot(vnorm[0]),6)) )


		# Define Zjj direction
		zjj = TLorentzVector()
		zjj = Zj1 + Zj2

		zjj.Boost(boost_ZZ);
		zjj_vect = TVector3( zjj.Vect().Unit() ) # zjj_vect has been boosted

		# Calcuate the normal to Zjj and z-direction plane
		zz2prime = TVector3((z_vect.Cross(zjj_vect)).Unit())  # zjj_vect here IS important

		# Calculate Phi1_zjj
		if abs(zjj_vect.Dot(zz2prime.Cross(vnorm[1])))>0:
			dsignhgg2 = zjj_vect.Dot(zz2prime.Cross(vnorm[1]))/(abs(zjj_vect.Dot(zz2prime.Cross(vnorm[1]))))  # zjj_vect here is NOT important
		else:
			dsignhgg2 = 0
		vPhi.append( dsignhgg2 * math.acos(zz2prime.Dot(vnorm[1])) )

	return vPhi



##########################################################################################
###########      FULL CALCULATION OF ALL VARIABLES, REPEATED FOR EACH SYS   ##############
##########################################################################################

def FullKinematicCalculation(T,variation):
	# Purpose: This is the magic function which calculates all kinematic quantities using
	#         the previous functions. It returns them as a simple list of doubles.
	#         It will be used in the loop over events. The 'variation' argument is passed
	#         along when getting the sets of leptons and jets, so the kinematics will vary.
	#         This function is repeated for all the sytematic variations inside the event
	#         loop. The return arguments ABSOLUELY MUST be in the same order they are
	#         listed in the branch declarations. Modify with caution.

	global isData

	#_passWptCut = checkWorZpt(T,0,100,'W')
	#_passZptCut = checkWorZpt(T,0,50,'Z')
	_WorZSystemPt = 0#T.LHE_Vpt # no longer exists?
        #print 'passWptCut:',_passWptCut

        #ptHat
	_ptHat = 0#fixme T.PtHat
	# MET as a vector
	met = MetVector(T)
	# ID Muons,Electrons
	[muons,goodmuoninds,met,trkisosMu,chargesMu,dpts,pfid,layers] = MediumIDMuons(T,met,variation,isData)
	# muons_forjetsep = MuonsForJetSeparation(T)
	# taus_forjetsep = TausForJetSeparation(T)
	[electrons,electroninds,met,trkisosEle,chargesEle,idIsoSFEle,idIsoSFEleUp,idIsoSFEleDown,hlt1SFEle,hlt1SFEleUp,hlt1SFEleDown,hlt2SFEle,hlt2SFEleUp,hlt2SFEleDown] = mvaWP90Electrons(T,met,variation,isData)
	# ID Jets and filter from leptons
	[jets,jetinds,met,failthreshold,neutralhadronEF,neutralemEF,btagCSVscores,btagMVAscores,btagSFsLoose,btagSFsMedium,btagSFsLoose_csv,btagSFsMedium_csv,btagRegSFs] = LooseIDJets(T,met,variation,isData)
	#jetsTemp = jets
	_jetCntPreFilter = len(jets)
	## jets = GeomFilterCollection(jets,muons_forjetsep,0.5)

#	[jets,btagCSVscores,btagMVAscores,btagSFsLoose,btagSFsMedium,btagSFsLoose_csv,btagSFsMedium_csv,btagRegSFs,jetinds] = GeomFilterCollection(jets,muons,0.3,btagCSVscores,btagMVAscores,btagSFsLoose,btagSFsMedium,btagSFsLoose_csv,btagSFsMedium_csv,btagRegSFs,jetinds)#fixme todo was 0.5 - changing to 0.3 following HH->wwbb. In any case 0.5 is too big now that cone size is 0.4 - put back in!
	#FIXME removing filter from electrons for now, since we don't use electron channel
#        [jets,btagCSVscores,btagMVAscores,btagSFsLoose,btagSFsMedium,btagSFsLoose_csv,btagSFsMedium_csv,btagRegSFs,jetinds] = GeomFilterCollection(jets,electrons,0.3,btagCSVscores,btagMVAscores,btagSFsLoose,btagSFsMedium,btagSFsLoose_csv,btagSFsMedium_csv,btagRegSFs,jetinds)#fixme todo was 0.5 - changing to 0.3 following HH->wwbb. In any case 0.5 is too big now that cone size is 0.4 - put back in!

	##[jetsTemp,jetinds] = GeomFilterCollection(jetsTemp,muons,0.3,jetinds)
	##[jetsTemp,jetinds] = GeomFilterCollection(jetsTemp,electrons,0.3,jetinds)
	## jets = GeomFilterCollection(jets,taus_forjetsep,0.5)
	# Empty lorentz vector for bookkeeping
	EmptyLorentz = TLorentzVector()
	EmptyLorentz.SetPtEtaPhiM(0,0,0,0)

	# Muon and Jet Counts
	_mucount = len(muons)
	_elcount = len(electrons)
	_jetcount = len(jets)
	#if v == '': print '_mucount',_mucount,'_elcount',_elcount,'_jetcount',_jetcount

	# Make sure there are two of every object, even if zero
	if len(muons) < 1 :
		muons.append(EmptyLorentz)
		trkisosMu.append(0.0)
		chargesMu.append(0.0)
		dpts.append(-1.0)
	if len(muons) < 2 :
		muons.append(EmptyLorentz)
		trkisosMu.append(0.0)
		chargesMu.append(0.0)
		dpts.append(-1.0)

	if len(electrons) < 1 :
		electrons.append(EmptyLorentz)
		trkisosEle.append(0.0)
		chargesEle.append(0.0)
		idIsoSFEle.append(0.0)
		idIsoSFEleUp.append(0.0)
		idIsoSFEleDown.append(0.0)
		hlt1SFEle.append(0.0)
		hlt1SFEleUp.append(0.0)
		hlt1SFEleDown.append(0.0)
		hlt2SFEle.append(0.0)
		hlt2SFEleUp.append(0.0)
		hlt2SFEleDown.append(0.0)
	if len(electrons) < 2 :
		electrons.append(EmptyLorentz)
		trkisosEle.append(0.0)
		chargesEle.append(0.0)
		idIsoSFEle.append(0.0)
		idIsoSFEleUp.append(0.0)
		idIsoSFEleDown.append(0.0)
		hlt1SFEle.append(0.0)
		hlt1SFEleUp.append(0.0)
		hlt1SFEleDown.append(0.0)
		hlt2SFEle.append(0.0)
		hlt2SFEleUp.append(0.0)
		hlt2SFEleDown.append(0.0)
	if len(jets) < 1 :
		jets.append(EmptyLorentz)
		neutralhadronEF.append(0.0)
		neutralemEF.append(0.0)
		btagCSVscores.append(-5.0)
		btagMVAscores.append(-5.0)
		jetinds.append(-1)
		btagSFsLoose.append([1.,1.,1.])
		btagSFsMedium.append([1.,1.,1.])
		btagSFsLoose_csv.append([1.,1.,1.])
		btagSFsMedium_csv.append([1.,1.,1.])
		btagRegSFs.append(-5.0)
	if len(jets) < 2 :
		jets.append(EmptyLorentz)
		neutralhadronEF.append(0.0)
		neutralemEF.append(0.0)
		btagCSVscores.append(-5.0)
		btagMVAscores.append(-5.0)
		jetinds.append(-1)
		btagSFsLoose.append([1.,1.,1.])
		btagSFsMedium.append([1.,1.,1.])
		btagSFsLoose_csv.append([1.,1.,1.])
		btagSFsMedium_csv.append([1.,1.,1.])
		btagRegSFs.append(-5.0)
	if len(jets) < 3 :
		jets.append(EmptyLorentz)
		neutralhadronEF.append(0.0)
		neutralemEF.append(0.0)
		btagCSVscores.append(-5.0)
		btagMVAscores.append(-5.0)
		jetinds.append(-1)
		btagSFsLoose.append([1.,1.,1.])
		btagSFsMedium.append([1.,1.,1.])
		btagSFsLoose_csv.append([1.,1.,1.])
		btagSFsMedium_csv.append([1.,1.,1.])
		btagRegSFs.append(-5.0)
	if len(jets) < 4 :
		jets.append(EmptyLorentz)
		neutralhadronEF.append(0.0)
		neutralemEF.append(0.0)
		btagCSVscores.append(-5.0)
		btagMVAscores.append(-5.0)
		jetinds.append(-1)
		btagSFsLoose.append([1.,1.,1.])
		btagSFsMedium.append([1.,1.,1.])
		btagSFsLoose_csv.append([1.,1.,1.])
		btagSFsMedium_csv.append([1.,1.,1.])
		btagRegSFs.append(-5.0)

	[_genMuons,_matchedRecoMuons,muonInd] = MuonsFromLQ(T)
	[_genJets,_matchedRecoJets,jetInd] = JetsFromLQ(T)
	[_genMuonsZ,_matchedRecoMuonsZ,muonIndZ,_genElectronsZ,_matchedRecoElectronsZ,electronIndZ,_genJetsH,_matchedRecoJetsH,jetIndH,_genJetsZ,_matchedRecoJetsZ,jetIndZ,onShellZMu,onShellZEle] = LeptonsAndJetsFromHH(T,4,isData)
	[ak8jetsH,ak8_matchedRecoJetH,ak8_jetIndH,ak8_matchedRecoJetZ,ak8_jetIndZ,_ak8_drujH_genMatched,_ak8_drujZ_genMatched,_ak8_drujH_gen,_ak8_drujZ_gen,_ak8_csvHj_genMatched,_ak8_csvZj_genMatched] = LeptonsAndJetsFromHH(T,8,isData)
	[_isElectronEvent_gen,_isMuonEvent_gen,_isTauEvent_gen]=getLeptonEventFlavorGEN(T)

	_muonInd1=muonInd[0]
	_muonInd2=muonInd[1]
	_jetInd1=jetInd[0]
	_jetInd2=jetInd[1]

	_ak8jetInd = ak8_jetIndH[0]
	_ak8jetZInd = ak8_jetIndZ[0]
	[_ak8_ptrecoj1] = [ak8jetsH[0].Pt()]
	[_ak8_ptHj_genMatched,_ak8_ptZj_genMatched]=[ak8_matchedRecoJetH[0].Pt(),ak8_matchedRecoJetZ[0].Pt()]
	[_ak8_etaHj_genMatched,_ak8_etaZj_genMatched]=[ak8_matchedRecoJetH[0].Eta(),ak8_matchedRecoJetZ[0].Eta()]
	[_ak8_phiHj_genMatched,_ak8_phiZj_genMatched]=[ak8_matchedRecoJetH[0].Phi(),ak8_matchedRecoJetZ[0].Phi()]
	[_ak8_massHj_genMatched,_ak8_massZj_genMatched]=[ak8_matchedRecoJetH[0].M(),ak8_matchedRecoJetZ[0].M()]

	[_ptu1_gen,_ptu2_gen] = [_genMuonsZ[0].Pt(),_genMuonsZ[1].Pt()]
	[_pte1_gen,_pte2_gen] = [_genElectronsZ[0].Pt(),_genElectronsZ[1].Pt()]
	[_ptHj1_gen,_ptHj2_gen,_ptZj1_gen,_ptZj2_gen]=[_genJetsH[0].Pt(),_genJetsH[1].Pt(),_genJetsZ[0].Pt(),_genJetsZ[1].Pt()]
	[_phiHj1_gen,_phiHj2_gen,_phiZj1_gen,_phiZj2_gen]=[_genJetsH[0].Phi(),_genJetsH[1].Phi(),_genJetsZ[0].Phi(),_genJetsZ[1].Phi()]
	[_etaHj1_gen,_etaHj2_gen,_etaZj1_gen,_etaZj2_gen]=[_genJetsH[0].Eta(),_genJetsH[1].Eta(),_genJetsZ[0].Eta(),_genJetsZ[1].Eta()]
	[_ptu1_genMatched,_ptu2_genMatched]=[_matchedRecoMuonsZ[0].Pt(),_matchedRecoMuonsZ[1].Pt()]
	[_pte1_genMatched,_pte2_genMatched]=[_matchedRecoElectronsZ[0].Pt(),_matchedRecoElectronsZ[1].Pt()]
	[_ptHj1_genMatched,_ptHj2_genMatched]=[_matchedRecoJetsH[0].Pt(),_matchedRecoJetsH[1].Pt()]
	[_ptZj1_genMatched,_ptZj2_genMatched]=[_matchedRecoJetsZ[0].Pt(),_matchedRecoJetsZ[1].Pt()]
	_dRu1Hj1_gen = abs(_genMuonsZ[0].DeltaR(_genJetsH[0]))
	_dRu1Hj2_gen = abs(_genMuonsZ[0].DeltaR(_genJetsH[1]))
	_dRu1Zj1_gen = abs(_genMuonsZ[0].DeltaR(_genJetsZ[0]))
	_dRu1Zj2_gen = abs(_genMuonsZ[0].DeltaR(_genJetsZ[1]))
	_dRu2Hj1_gen = abs(_genMuonsZ[1].DeltaR(_genJetsH[0]))
	_dRu2Hj2_gen = abs(_genMuonsZ[1].DeltaR(_genJetsH[1]))
	_dRu2Zj1_gen = abs(_genMuonsZ[1].DeltaR(_genJetsZ[0]))
	_dRu2Zj2_gen = abs(_genMuonsZ[1].DeltaR(_genJetsZ[1]))
	_dRu1Hj1_genMatched = abs(_matchedRecoMuonsZ[0].DeltaR(_matchedRecoJetsH[0]))
	_dRu1Hj2_genMatched = abs(_matchedRecoMuonsZ[0].DeltaR(_matchedRecoJetsH[1]))
	_dRu1Zj1_genMatched = abs(_matchedRecoMuonsZ[0].DeltaR(_matchedRecoJetsZ[0]))
	_dRu1Zj2_genMatched = abs(_matchedRecoMuonsZ[0].DeltaR(_matchedRecoJetsZ[1]))
	_dRu2Hj1_genMatched = abs(_matchedRecoMuonsZ[1].DeltaR(_matchedRecoJetsH[0]))
	_dRu2Hj2_genMatched = abs(_matchedRecoMuonsZ[1].DeltaR(_matchedRecoJetsH[1]))
	_dRu2Zj1_genMatched = abs(_matchedRecoMuonsZ[1].DeltaR(_matchedRecoJetsZ[0]))
	_dRu2Zj2_genMatched = abs(_matchedRecoMuonsZ[1].DeltaR(_matchedRecoJetsZ[1]))
	_dRe1Hj1_gen = abs(_genElectronsZ[0].DeltaR(_genJetsH[0]))
	_dRe1Hj2_gen = abs(_genElectronsZ[0].DeltaR(_genJetsH[1]))
	_dRe1Zj1_gen = abs(_genElectronsZ[0].DeltaR(_genJetsZ[0]))
	_dRe1Zj2_gen = abs(_genElectronsZ[0].DeltaR(_genJetsZ[1]))
	_dRe2Hj1_gen = abs(_genElectronsZ[1].DeltaR(_genJetsH[0]))
	_dRe2Hj2_gen = abs(_genElectronsZ[1].DeltaR(_genJetsH[1]))
	_dRe2Zj1_gen = abs(_genElectronsZ[1].DeltaR(_genJetsZ[0]))
	_dRe2Zj2_gen = abs(_genElectronsZ[1].DeltaR(_genJetsZ[1]))
	_dRe1Hj1_genMatched = abs(_matchedRecoElectronsZ[0].DeltaR(_matchedRecoJetsH[0]))
	_dRe1Hj2_genMatched = abs(_matchedRecoElectronsZ[0].DeltaR(_matchedRecoJetsH[1]))
	_dRe1Zj1_genMatched = abs(_matchedRecoElectronsZ[0].DeltaR(_matchedRecoJetsZ[0]))
	_dRe1Zj2_genMatched = abs(_matchedRecoElectronsZ[0].DeltaR(_matchedRecoJetsZ[1]))
	_dRe2Hj1_genMatched = abs(_matchedRecoElectronsZ[1].DeltaR(_matchedRecoJetsH[0]))
	_dRe2Hj2_genMatched = abs(_matchedRecoElectronsZ[1].DeltaR(_matchedRecoJetsH[1]))
	_dRe2Zj1_genMatched = abs(_matchedRecoElectronsZ[1].DeltaR(_matchedRecoJetsZ[0]))
	_dRe2Zj2_genMatched = abs(_matchedRecoElectronsZ[1].DeltaR(_matchedRecoJetsZ[1]))


	leptons,_genLeptonsZ,_matchedRecoLeptonsZ=[],[],[]
	_isMuonEvent,_isElectronEvent = False,False
	#if muons[0].Pt()>=electrons[0].Pt() or electrons[1].Pt()<1:#prioritize muons: cases where muon1 pt > ele1 pt, or where there is no 2nd electron
	#	if electrons[0]>16 and electrons[1]>8 and muons[1]<8:#single case where first muon pt is higher, but there is only one good muon and 2 valid electrons
	#		leptons = electrons
	#		charges = chargesEle
	#		trkisos = trkisosEle
	#		_genLeptonsZ=_genElectronsZ
	#		_matchedRecoLeptonsZ=_matchedRecoElectronsZ
	#		_isElectronEvent=True
	#	else:
	#		leptons = muons
	#		charges = chargesMu
	#		trkisos = trkisosMu
	#		_genLeptonsZ=_genMuonsZ
	#		_matchedRecoLeptonsZ=_matchedRecoMuonsZ
	#		_isMuonEvent=True
	#else:#cases where ele1 pt > muon1 pt
	#	if muons[0]>16 and muons[1]>8 and electrons[1]<8:#single case where first electron pt is higher, but there is only one good electron and 2 valid muons
	#		leptons = muons
	#		charges = chargesMu
	#		trkisos = trkisosMu
	#		_genLeptonsZ=_genMuonsZ
	#		_matchedRecoLeptonsZ=_matchedRecoMuonsZ
	#		_isMuonEvent=True
	#	else:
	#		leptons = electrons
	#		charges = chargesEle
	#		trkisos = trkisosEle
	#		_genLeptonsZ=_genElectronsZ
	#		_matchedRecoLeptonsZ=_matchedRecoElectronsZ
	#		_isElectronEvent=True

	if electrons[0].Pt()>25 and electrons[1].Pt()>15:
		leptons = electrons
		charges = chargesEle
		trkisos = trkisosEle
		_genLeptonsZ=_genElectronsZ
		_matchedRecoLeptonsZ=_matchedRecoElectronsZ
		_isElectronEvent=True
	if muons[0].Pt()>20 and muons[1].Pt()>10:
		leptons = muons
		charges = chargesMu
		trkisos = trkisosMu
		_genLeptonsZ=_genMuonsZ
		_matchedRecoLeptonsZ=_matchedRecoMuonsZ
		_isMuonEvent=True
	else:
		leptons = [EmptyLorentz,EmptyLorentz]
		charges = [0,0]
		trkisos = [-999,-999]
		_genLeptonsZ=[EmptyLorentz,EmptyLorentz]
		_matchedRecoLeptonsZ=[EmptyLorentz,EmptyLorentz]

	# Get kinematic quantities
#	[_passMedIdmu1,_passMedIdmu1,_passMedId2016mu1,_passMedId2016mu1]=[passMedIds[0],passMedIds[1],passMedId2016s[0],passMedId2016s[1]]

	[_ptmu1,_etamu1,_phimu1,_isomu1,_qmu1,_dptmu1] = [muons[0].Pt(),muons[0].Eta(),muons[0].Phi(),trkisosMu[0],chargesMu[0],dpts[0]]
	[_ptmu2,_etamu2,_phimu2,_isomu2,_qmu2,_dptmu2] = [muons[1].Pt(),muons[1].Eta(),muons[1].Phi(),trkisosMu[1],chargesMu[1],dpts[1]]

#	[_ispfmu1,ispfmu2] = [pfid[0],pfid[1]]
#	[_layersmu1,_layersmu2] = [layers[0],layers[1]]

	[_ptele1,_etaele1,_phiele1,_isoele1,_qele1] = [electrons[0].Pt(),electrons[0].Eta(),electrons[0].Phi(),trkisosEle[0],chargesEle[0]]
	[_ptele2,_etaele2,_phiele2,_isoele2,_qele2] = [electrons[1].Pt(),electrons[1].Eta(),electrons[1].Phi(),trkisosEle[1],chargesEle[1]]

	[_ele1IDandIsoSF,_ele1IDandIsoSFup,_ele1IDandIsoSFdown]=[idIsoSFEle[0],idIsoSFEleUp[0],idIsoSFEleDown[0]]
	[_ele2IDandIsoSF,_ele2IDandIsoSFup,_ele2IDandIsoSFdown]=[idIsoSFEle[1],idIsoSFEleUp[1],idIsoSFEleDown[1]]

	[_ele1hltSF,_ele1hltSFup,_ele1hltSFdown]=[hlt1SFEle[0],hlt1SFEleUp[0],hlt1SFEleDown[0]]
	[_ele2hltSF,_ele2hltSFup,_ele2hltSFdown]=[hlt2SFEle[1],hlt2SFEleUp[1],hlt2SFEleDown[1]]

	[_ptlep1,_etalep1,_philep1,_isolep1,_qlep1] = [leptons[0].Pt(),leptons[0].Eta(),leptons[0].Phi(),trkisos[0],charges[0]]
	[_ptlep2,_etalep2,_philep2,_isolep2,_qlep2] = [leptons[1].Pt(),leptons[1].Eta(),leptons[1].Phi(),trkisos[1],charges[1]]

	[_ptj1,_etaj1,_phij1]    = [jets[0].Pt(),jets[0].Eta(),jets[0].Phi()]
	[_ptj2,_etaj2,_phij2]    = [jets[1].Pt(),jets[1].Eta(),jets[1].Phi()]
	[_ptj3,_ptj4] = [0.,0.]
	if len(jets) > 2 :
		_ptj3 = jets[2].Pt()
	if len(jets) > 3 :
		_ptj4 = jets[3].Pt()

	[_nhefj1,_nhefj2,_nemefj1,_nemefj2] = [neutralhadronEF[0],neutralhadronEF[1],neutralemEF[0],neutralemEF [1]]
	[_ptmet,_etamet,_phimet] = [met.Pt(),0,met.Phi()]
	[_xmiss,_ymiss] = [met.Px(),met.Py()]
	[_CSVj1,_CSVj2] = [btagCSVscores[0],btagCSVscores[1]]
	[_bMVAj1,_bMVAj2] = [btagMVAscores[0],btagMVAscores[1]]

	_stuujj = ST([muons[0],muons[1],jets[0],jets[1]])

	_steejj = ST([electrons[0],electrons[1],jets[0],jets[1]])

	_stlljj = ST([leptons[0],leptons[1],jets[0],jets[1]])

	_Muu = (muons[0]+muons[1]).M()
	_MTuv = TransMass(muons[0],met)
	_Mjj = (jets[0]+jets[1]).M()

	_DRuu = (muons[0]).DeltaR(muons[1])
	_DPHIuv = abs((muons[0]).DeltaPhi(met))
	_DPHIj1v = abs((jets[0]).DeltaPhi(met))
	_DPHIj2v = abs((jets[1]).DeltaPhi(met))

	_Mee = (electrons[0]+electrons[1]).M()
	_DRee = (electrons[0]).DeltaR(electrons[1])
	_DPHIev = abs((electrons[0]).DeltaPhi(met))

	_Mll = (leptons[0]+leptons[1]).M()
	_DRll = (leptons[0]).DeltaR(leptons[1])

	_DRu1j1 = abs(muons[0].DeltaR(jets[0]))
	_DRu1j2 = abs(muons[0].DeltaR(jets[1]))
	_DRu2j1 = abs(muons[1].DeltaR(jets[0]))
	_DRu2j2 = abs(muons[1].DeltaR(jets[1]))

	_DRj1j2   = abs(jets[0].DeltaR(jets[1]))
	_DPhij1j2 = abs(jets[0].DeltaPhi(jets[1]))

	_DPhiu1j1 = abs(muons[0].DeltaPhi(jets[0]))
	_DPhiu1j2 = abs(muons[0].DeltaPhi(jets[1]))
	_DPhiu2j1 = abs(muons[1].DeltaPhi(jets[0]))
	_DPhiu2j2 = abs(muons[1].DeltaPhi(jets[1]))

	_DRe1j1 = abs(electrons[0].DeltaR(jets[0]))
	_DRe1j2 = abs(electrons[0].DeltaR(jets[1]))
	_DRe2j1 = abs(electrons[1].DeltaR(jets[0]))
	_DRe2j2 = abs(electrons[1].DeltaR(jets[1]))
	_DPhie1j1 = abs(electrons[0].DeltaPhi(jets[0]))
	_DPhie1j2 = abs(electrons[0].DeltaPhi(jets[1]))
	_DPhie2j1 = abs(electrons[1].DeltaPhi(jets[0]))
	_DPhie2j2 = abs(electrons[1].DeltaPhi(jets[1]))

	_DRl1j1 = abs(leptons[0].DeltaR(jets[0]))
	_DRl1j2 = abs(leptons[0].DeltaR(jets[1]))
	_DRl2j1 = abs(leptons[1].DeltaR(jets[0]))
	_DRl2j2 = abs(leptons[1].DeltaR(jets[1]))
	_DPhil1j1 = abs(leptons[0].DeltaPhi(jets[0]))
	_DPhil1j2 = abs(leptons[0].DeltaPhi(jets[1]))
	_DPhil2j1 = abs(leptons[1].DeltaPhi(jets[0]))
	_DPhil2j2 = abs(leptons[1].DeltaPhi(jets[1]))

	_Muu_gen,_Mee_gen=0,0
	_Muu_genMatched,_Mee_genMatched=0,0


	if len(electrons)>=1 :
		_pte1 = electrons[0].Pt()
		if len(electrons)>=2 : _pte2 = electrons[1].Pt()
		else : _pte2 = 0.
	else :
		_pte1 = 0.


	[bjet1,bscore1,bscoreMVA1,bjet2,bscore2,bscoreMVA2,jet1,jet2,jet3,indRecoBJet1,indRecoBJet2,indRecoJet1,indRecoJet2,indRecoJet3] = [EmptyLorentz,-5.0,-5.0,EmptyLorentz,-5.0,-5.0,EmptyLorentz,EmptyLorentz,EmptyLorentz,-1,-1,-1,-1,-1]
	[unreg_bjet1,unreg_bjet2] = [EmptyLorentz,EmptyLorentz]

	[unreg_bjet1,bscore1,bscoreMVA1,unreg_bjet2,bscore2,bscoreMVA2,jet1,jet2,jet3,_cisv_Zjet1,_cisv_Zjet2,_cmva_Zjet1,_cmva_Zjet2,indRecoBJet1,indRecoBJet2,indRecoJet1,indRecoJet2,indRecoJet3,bjet1,bjet2,_Hjet1BtagSFL,_Hjet1BtagSFM,_Hjet2BtagSFL,_Hjet2BtagSFM,_Zjet1BtagSFL,_Zjet1BtagSFM,_Zjet2BtagSFL,_Zjet2BtagSFM,_Hjet1BtagSFL_csv,_Hjet1BtagSFM_csv,_Hjet2BtagSFL_csv,_Hjet2BtagSFM_csv,_Zjet1BtagSFL_csv,_Zjet1BtagSFM_csv,_Zjet2BtagSFL_csv,_Zjet2BtagSFM_csv] = GetHHJetsNew(jets,btagCSVscores,btagMVAscores,btagSFsLoose,btagSFsMedium,btagSFsLoose_csv,btagSFsMedium_csv,btagRegSFs,muons[0],muons[1],electrons[0],electrons[1],_isMuonEvent,_isElectronEvent,jetinds, T, met)

	[_Hjet1BsfLoose,_Hjet1BsfLooseUp,_Hjet1BsfLooseDown] = _Hjet1BtagSFL
	[_Hjet1BsfMedium,_Hjet1BsfMediumUp,_Hjet1BsfMediumDown] = _Hjet1BtagSFM
	[_Hjet2BsfLoose,_Hjet2BsfLooseUp,_Hjet2BsfLooseDown] = _Hjet2BtagSFL
	[_Hjet2BsfMedium,_Hjet2BsfMediumUp,_Hjet2BsfMediumDown] = _Hjet2BtagSFM

	[_Zjet1BsfLoose,_Zjet1BsfLooseUp,_Zjet1BsfLooseDown] = _Zjet1BtagSFL
	[_Zjet1BsfMedium,_Zjet1BsfMediumUp,_Zjet1BsfMediumDown] = _Zjet1BtagSFM
	[_Zjet2BsfLoose,_Zjet2BsfLooseUp,_Zjet2BsfLooseDown] = _Zjet2BtagSFL
	[_Zjet2BsfMedium,_Zjet2BsfMediumUp,_Zjet2BsfMediumDown] = _Zjet2BtagSFM

	[_Hjet1BsfLoose_csv,_Hjet1BsfLooseUp_csv,_Hjet1BsfLooseDown_csv] = _Hjet1BtagSFL_csv
	[_Hjet1BsfMedium_csv,_Hjet1BsfMediumUp_csv,_Hjet1BsfMediumDown_csv] = _Hjet1BtagSFM_csv
	[_Hjet2BsfLoose_csv,_Hjet2BsfLooseUp_csv,_Hjet2BsfLooseDown_csv] = _Hjet2BtagSFL_csv
	[_Hjet2BsfMedium_csv,_Hjet2BsfMediumUp_csv,_Hjet2BsfMediumDown_csv] = _Hjet2BtagSFM_csv

	[_Zjet1BsfLoose_csv,_Zjet1BsfLooseUp_csv,_Zjet1BsfLooseDown_csv] = _Zjet1BtagSFL_csv
	[_Zjet1BsfMedium_csv,_Zjet1BsfMediumUp_csv,_Zjet1BsfMediumDown_csv] = _Zjet1BtagSFM_csv
	[_Zjet2BsfLoose_csv,_Zjet2BsfLooseUp_csv,_Zjet2BsfLooseDown_csv] = _Zjet2BtagSFL_csv
	[_Zjet2BsfMedium_csv,_Zjet2BsfMediumUp_csv,_Zjet2BsfMediumDown_csv] = _Zjet2BtagSFM_csv

	"""
	#if muons[0].Pt()>20 and muons[1].Pt()>10 and variation=='':
	if variation=='':
		print '    bjet1score, bjet2score, Hmass, Zmass, ZMuMass, uu4jMass, indexbj1, indexbj2, indexj1, indexj2, indexj3 '
		print '1: ',bscore1,bscore2,(bjet1+bjet2).M(),(jet1+jet2).M(),(muons[0]+muons[1]).M(),(muons[0]+muons[1]+jet1+jet2).M(),indRecoBJet1,indRecoBJet2,indRecoJet1,indRecoJet2,indRecoJet3,bjet1.Pt(),bjet2.Pt(),jet1.Pt(),jet2.Pt(),jet3.Pt(), ' ' ,jetIndH[0],jetIndH[1],jetIndZ[0],jetIndZ[1]

		print '2: ',bscore1_2,bscore2_2,(bjet1_2+bjet2_2).M(),(jet1_2+jet2_2).M(),(muons[0]+muons[1]).M(),(muons[0]+muons[1]+jet1_2+jet2_2).M()
		print '3: ',bscore1_3,bscore2_3,(bjet1_3+bjet2_3).M(),(jet1_3+jet2_3).M(),(muons[0]+muons[1]).M(),(muons[0]+muons[1]+jet1_3+jet2_3).M()
		print ''
	"""

	CorHj1Avail,CorHj2Avail  = False,False
	CorZj1Avail,CorZj2Avail  = False,False
	for j in jetinds :
		if jetIndH[0] == j: CorHj1Avail=True
		if jetIndH[1] == j: CorHj2Avail=True
		if jetIndZ[0] == j: CorZj1Avail=True
		if jetIndZ[1] == j: CorZj2Avail=True

	_CorHj1j2Avail = CorHj1Avail and CorHj2Avail
	_CorZj1j2Avail = CorZj1Avail and CorZj2Avail

	[_bscoreMVA1_genMatched, _bscoreMVA2_genMatched, tempBscore1, tempBscore2] = [-5.0,-5.0,-5.0,-5.0]
	if jetIndH[0] >= 0 :
		tempBscore1 = T.Jet_btagCMVA[jetIndH[0]]
		_bscoreMVA1_genMatched = T.Jet_btagCMVA[jetIndH[0]]
	if jetIndH[1] >= 0 :
		tempBscore2 = T.Jet_btagCMVA[jetIndH[1]]
		_bscoreMVA2_genMatched = T.Jet_btagCMVA[jetIndH[1]]
	if tempBscore1 < tempBscore2 : # becareful if you want to do this. I have NOT re-ordered all variables.
		_bscoreMVA1_genMatched = tempBscore2
		_bscoreMVA2_genMatched = tempBscore1

	[_Hj1Matched,_Hj2Matched,_Zj1Matched,_Zj2Matched] = [0,0,0,0]
	if indRecoBJet1 == jetIndH[0] or indRecoBJet1 == jetIndH[1]: _Hj1Matched=1
	if indRecoBJet2 == jetIndH[1] or indRecoBJet2 == jetIndH[0]: _Hj2Matched=1
	if indRecoJet1  == jetIndZ[0] or indRecoJet1  == jetIndZ[1]: _Zj1Matched=1
	if indRecoJet2  == jetIndZ[1] or indRecoJet2  == jetIndZ[0]: _Zj2Matched=1
	[_Hj1Present,_Hj2Present,_Zj1Present,_Zj2Present]=[ bjet1.Pt()>0, bjet2.Pt()>0, jet1.Pt()>0, jet2.Pt()>0 ]

	#if v == '' : print 'CorHj1Avail',CorHj1Avail,'CorHj2Avail',CorHj2Avail,'CorHj1j2Avail',_CorHj1j2Avail
	#if jetIndH[0] >= 0 and jetIndH[1] >= 0 and jetIndZ[0] >= 0 and jetIndZ[1] >= 0 :
	#if jetIndH[0] >= 0 and jetIndH[1] >= 0 and _CorHj1j2Avail and (not (_Hj1Matched and _Hj2Matched)) and len(goodmuoninds) >= 2:

#	if jetIndH[0] >= 0 and jetIndH[1] >= 0 and _CorHj1j2Avail and len(goodmuoninds) >= 2:
#
#		if v == '' :
#			print ' dR gen jet:', abs(_genJetsH[0].DeltaR(_genJetsH[1]))
#			for i in range(len(jets)) :
#				if T.PFJetPartonFlavourAK4CHS[jetinds[i]] == 21: continue
#				#if T.PFJetCombinedInclusiveSecondaryVertexBTagAK4CHS[jetinds[i]] < 0.06: continue
#				print '   After Filter Recojet index',jetinds[i], 'flavor', T.PFJetPartonFlavourAK4CHS[jetinds[i]],  'pt',jets[i].Pt(),'eta',jets[i].Eta(), 'phi',jets[i].Phi() ,'btagScores', btagMVAscores[i], 'CSVScore', btagCSVscores[i], 'pileupMVA',T.PFJetPileupMVAAK4CHS[jetinds[i]], T.PFJetPileupMVApassesLooseAK4CHS[jetinds[i]],T.PFJetPileupMVApassesMediumAK4CHS[jetinds[i]],T.PFJetPileupMVApassesTightAK4CHS[jetinds[i]]
#
#			print 'matched bjet indices:',jetIndH
#			print 'matched  jet indices:',jetIndZ
#			print 'reco     jet indices:',jetinds
#			print 'getHH    jet indices:',indRecoBJet1,indRecoBJet2,indRecoJet1,indRecoJet2
#			print ''
#			print 'good muons   indices:',goodmuoninds
#			print 'good elects  indices:',electroninds
#			print ''


	[_Muu4j,_Mee4j,_Mll4j] = [0., 0., 0.]
	#if len(jets)>=4 and ( len(muons)>=2 or len(electrons)>=2 ):
	#	if len(muons)>=2 :
	#		_Muu4j = (muons[0]+muons[1]+jets[0]+jets[1]+jets[2]+jets[3]).M()
	#	if len(electrons)>=2 :
	#		_Mee4j = (electrons[0]+electrons[1]+jets[0]+jets[1]+jets[2]+jets[3]).M()
	#	if _ptmu1 > _pte1 and len(muons)>=2:
	#		_Mll4j = (muons[0]+muons[1]+jets[0]+jets[1]+jets[2]+jets[3]).M()
	#	elif _pte1 > _ptmu1 and len(electrons)>=2 :
	#		_Mll4j = (electrons[0]+electrons[1]+jets[0]+jets[1]+jets[2]+jets[3]).M()
	_Muu4j = (muons[0]+muons[1]+bjet1+bjet2+jet1+jet2).M()
	_Mee4j = (electrons[0]+electrons[1]+bjet1+bjet2+jet1+jet2).M()
	_Mll4j = (leptons[0]+leptons[1]+bjet1+bjet2+jet1+jet2).M()
	_Muujj = (muons[0]+muons[1]+jet1+jet2).M()
	_Meejj = (electrons[0]+electrons[1]+jet1+jet2).M()
	_Mlljj = (leptons[0]+leptons[1]+jet1+jet2).M()
	_Mbb_H = (bjet1+bjet2).M()
	_Mbb_H_orig = (unreg_bjet1+unreg_bjet2).M()
	_Muu4j_orig = (muons[0]+muons[1]+unreg_bjet1+unreg_bjet2+jet1+jet2).M()
	_dRbb_H = abs(bjet1.DeltaR(bjet2))
	_dPhibb_H = abs(bjet1.DeltaPhi(bjet2))
	_Mjj_Z = (jet1+jet2).M()
	_Mjj_Z_3jet = min(abs((jet1+jet2).M()-91.),abs((jet1+jet3).M()-91.),abs((jet2+jet3).M()-91.))
	_dRjj_Z = abs(jet1.DeltaR(jet2))
	_dPhijj_Z = abs(jet1.DeltaPhi(jet2))
	_dRu1Hj1 = abs(muons[0].DeltaR(bjet1))
	_dRu1Hj2 = abs(muons[0].DeltaR(bjet2))
	_dRu1Zj1 = abs(muons[0].DeltaR(jet1))
	_dRu1Zj2 = abs(muons[0].DeltaR(jet2))
	_dRu2Hj1 = abs(muons[1].DeltaR(bjet1))
	_dRu2Hj2 = abs(muons[1].DeltaR(bjet2))
	_dRu2Zj1 = abs(muons[1].DeltaR(jet1))
	_dRu2Zj2 = abs(muons[1].DeltaR(jet2))
	_dRe1Hj1 = abs(electrons[0].DeltaR(bjet1))
	_dRe1Hj2 = abs(electrons[0].DeltaR(bjet2))
	_dRe1Zj1 = abs(electrons[0].DeltaR(jet1))
	_dRe1Zj2 = abs(electrons[0].DeltaR(jet2))
	_dRe2Hj1 = abs(electrons[1].DeltaR(bjet1))
	_dRe2Hj2 = abs(electrons[1].DeltaR(bjet2))
	_dRe2Zj1 = abs(electrons[1].DeltaR(jet1))
	_dRe2Zj2 = abs(electrons[1].DeltaR(jet2))

	_stuu4j = ST([muons[0],muons[1],bjet1,bjet2,jet1,jet2])
	_stee4j = ST([electrons[0],electrons[1],bjet1,bjet2,jet1,jet2])
	_stll4j = ST([leptons[0],leptons[1],bjet1,bjet2,jet1,jet2])
	[_Pt_origHjet1,_Pt_origHjet2] = [unreg_bjet1.Pt(),unreg_bjet2.Pt()] # keep only the original bjets pt
	[_Pt_Hjet1,_Pt_Hjet2,_Pt_Zjet1,_Pt_Zjet2] = [bjet1.Pt(),bjet2.Pt(),jet1.Pt(),jet2.Pt()]
	[_Pt_Hjets,_Pt_Zjets] = [(bjet1+bjet2).Pt(),(jet1+jet2).Pt()]
	[_Pt_uu,_Pt_ee,_Pt_ll] = [(muons[0]+muons[1]).Pt(),(electrons[0]+electrons[1]).Pt(),(leptons[0]+leptons[1]).Pt()]

	[_phiHj1,_phiHj2,_phiZj1,_phiZj2]=[bjet1.Phi(),bjet2.Phi(),jet1.Phi(),jet2.Phi()]
	[_etaHj1,_etaHj2,_etaZj1,_etaZj2]=[bjet1.Eta(),bjet2.Eta(),jet1.Eta(),jet2.Eta()]

	_dRuubb_H = abs((muons[0]+muons[1]).DeltaR(bjet1+bjet2))
	_dRuujj_Z = abs((muons[0]+muons[1]).DeltaR(jet1+jet2))
	_dPHIuubb_H = abs((muons[0]+muons[1]).DeltaPhi(bjet1+bjet2))
	_dPHIuujj_Z = abs((muons[0]+muons[1]).DeltaPhi(jet1+jet2))

	_dReebb_H = abs((electrons[0]+electrons[1]).DeltaR(bjet1+bjet2))
	_dReejj_Z = abs((electrons[0]+electrons[1]).DeltaR(jet1+jet2))
	_dPHIeebb_H = abs((electrons[0]+electrons[1]).DeltaPhi(bjet1+bjet2))
	_dPHIeejj_Z = abs((electrons[0]+electrons[1]).DeltaPhi(jet1+jet2))

	_dRllbb_H = abs((leptons[0]+leptons[1]).DeltaR(bjet1+bjet2))
	_dRlljj_Z = abs((leptons[0]+leptons[1]).DeltaR(jet1+jet2))
	_dPHIllbb_H = abs((leptons[0]+leptons[1]).DeltaPhi(bjet1+bjet2))
	_dPHIlljj_Z = abs((leptons[0]+leptons[1]).DeltaPhi(jet1+jet2))

	_minDRuj = abs(min(muons[0].DeltaR(jet1),muons[0].DeltaR(jet2),muons[1].DeltaR(jet1),muons[1].DeltaR(jet2)))
	_minDRej = abs(min(electrons[0].DeltaR(jet1),electrons[0].DeltaR(jet2),electrons[1].DeltaR(jet1),electrons[1].DeltaR(jet2)))
	_minDRlj = abs(min(leptons[0].DeltaR(jet1),leptons[0].DeltaR(jet2),leptons[1].DeltaR(jet1),leptons[1].DeltaR(jet2)))

	_cosThetaStarMu  = getCosThetaStar_CS(bjet1+bjet2,muons[0]+muons[1]+jet1+jet2)
	_cosThetaStarEle = getCosThetaStar_CS(bjet1+bjet2,electrons[0]+electrons[1]+jet1+jet2)
	_cosThetaStarLep = getCosThetaStar_CS(bjet1+bjet2,leptons[0]+leptons[1]+jet1+jet2)

	#### AH ####
	############# hh angular variables #####################
	_cosThetaStarMu_gen = getCosThetaStar_CS(_genJetsH[0]+_genJetsH[1], _genMuonsZ[0]+_genMuonsZ[1]+_genJetsZ[0]+_genJetsZ[1])
	_cosThetaStarEle_gen = getCosThetaStar_CS(_genJetsH[0]+_genJetsH[1],_genElectronsZ[0]+_genElectronsZ[1]+_genJetsZ[0]+_genJetsZ[1])

	cosThetaAngles_uu_gen = CosThetaAngles(_genJetsH[0], _genJetsH[1], _genJetsZ[0], _genJetsZ[1], _genMuonsZ[0], _genMuonsZ[1])
	_cosThetaStar_uu_gen = cosThetaAngles_uu_gen[0]
	_cosTheta_hbb_uu_gen = cosThetaAngles_uu_gen[1]
	_cosTheta_zjj_hzz_uu_gen  = cosThetaAngles_uu_gen[2]
	_cosTheta_zuu_hzz_gen  = cosThetaAngles_uu_gen[3]
	_cosTheta_zj1_hzz_uu_gen  = cosThetaAngles_uu_gen[4]
	_cosTheta_zu1_hzz_gen  = cosThetaAngles_uu_gen[5]
	cosThetaAngles_uu = CosThetaAngles(bjet1, bjet2, jet1, jet2, muons[0], muons[1])
	_cosThetaStar_uu = cosThetaAngles_uu[0]
	_cosTheta_hbb_uu  = cosThetaAngles_uu[1]
	_cosTheta_zjj_hzz_uu  = cosThetaAngles_uu[2]
	_cosTheta_zuu_hzz  = cosThetaAngles_uu[3]
	_cosTheta_zj1_hzz_uu  = cosThetaAngles_uu[4]
	_cosTheta_zu1_hzz  = cosThetaAngles_uu[5]

	cosThetaAngles_ee_gen = CosThetaAngles(_genJetsH[0], _genJetsH[1], _genJetsZ[0], _genJetsZ[1], _genElectronsZ[0], _genElectronsZ[1])
	_cosThetaStar_ee_gen = cosThetaAngles_ee_gen[0]
	_cosTheta_hbb_ee_gen = cosThetaAngles_ee_gen[1]
	_cosTheta_zjj_hzz_ee_gen  = cosThetaAngles_ee_gen[2]
	_cosTheta_zee_hzz_gen  = cosThetaAngles_ee_gen[3]
	_cosTheta_zj1_hzz_ee_gen  = cosThetaAngles_ee_gen[4]
	_cosTheta_ze1_hzz_gen  = cosThetaAngles_ee_gen[5]
	cosThetaAngles_ee = CosThetaAngles(bjet1, bjet2, jet1, jet2, electrons[0], electrons[1])
	_cosThetaStar_ee = cosThetaAngles_ee[0]
	_cosTheta_hbb_ee  = cosThetaAngles_ee[1]
	_cosTheta_zjj_hzz_ee  = cosThetaAngles_ee[2]
	_cosTheta_zee_hzz  = cosThetaAngles_ee[3]
	_cosTheta_zj1_hzz_ee  = cosThetaAngles_ee[4]
	_cosTheta_ze1_hzz  = cosThetaAngles_ee[5]

	phiAngles_uu_gen = getPhi(_genJetsH[0], _genJetsH[1], _genJetsZ[0], _genJetsZ[1], _genMuonsZ[0], _genMuonsZ[1])
	_phi0_uu_gen = phiAngles_uu_gen[0]
	_phi1_uu_gen = phiAngles_uu_gen[1]
	phiAngles_uu = getPhi(bjet1, bjet2, jet1, jet2, muons[0], muons[1])
	_phi0_uu = phiAngles_uu[0]
	_phi1_uu = phiAngles_uu[1]

	phiAngles_ee_gen = getPhi(_genJetsH[0], _genJetsH[1], _genJetsZ[0], _genJetsZ[1], _genElectronsZ[0], _genElectronsZ[1])
	_phi0_ee_gen = phiAngles_ee_gen[0]
	_phi1_ee_gen = phiAngles_ee_gen[1]
	phiAngles_ee = getPhi(bjet1, bjet2, jet1, jet2, electrons[0], electrons[1])
	_phi0_ee = phiAngles_ee[0]
	_phi1_ee = phiAngles_ee[1]

	### Using the ZZ->uujj system instead of the HH system
	_cosThetaStarZuu_CS_gen = getCosThetaStar_CS(_genMuonsZ[0]+_genMuonsZ[1], _genJetsZ[0]+_genJetsZ[1])
	_cosThetaStarZjj_CS_uu_gen = getCosThetaStar_CS(_genJetsZ[0]+_genJetsZ[1], _genMuonsZ[0]+_genMuonsZ[1])
	_cosThetaStarZuu_CS = getCosThetaStar_CS(muons[0]+muons[1], jet1+jet2)
	_cosThetaStarZjj_CS_uu = getCosThetaStar_CS(jet1+jet2, muons[0]+muons[1])

	cosThetaAng_ZZ_uu_gen = CosThetaAngles_ZZ(_genJetsZ[0], _genJetsZ[1], _genMuonsZ[0], _genMuonsZ[1])
	_cosTheta_Zuu_gen = cosThetaAng_ZZ_uu_gen[0]
	_cosTheta_Zjj_uu_gen = cosThetaAng_ZZ_uu_gen[1]
	cosThetaAng_ZZ_uu = CosThetaAngles_ZZ(jet1, jet2, muons[0], muons[1])
	_cosTheta_Zuu = cosThetaAng_ZZ_uu[0]
	_cosTheta_Zjj_uu = cosThetaAng_ZZ_uu[1]

	phiAngles_ZZ_uu_gen = getPhi_ZZ(_genJetsZ[0], _genJetsZ[1], _genMuonsZ[0], _genMuonsZ[1])
	_phi0_zz_uu_gen = phiAngles_ZZ_uu_gen[0]
	_phi1_zuu_gen = phiAngles_ZZ_uu_gen[1]
	_phi1_zjj_uu_gen = phiAngles_ZZ_uu_gen[2]
	phiAngles_ZZ_uu = getPhi_ZZ(jet1, jet2, muons[0], muons[1])
	_phi0_zz_uu  = phiAngles_ZZ_uu[0]
	_phi1_zuu = phiAngles_ZZ_uu[1]
	_phi1_zjj_uu = phiAngles_ZZ_uu[2]

	### Using the ZZ->eejj system instead of the HH system
	_cosThetaStarZee_CS_gen = getCosThetaStar_CS(_genElectronsZ[0]+_genElectronsZ[1], _genJetsZ[0]+_genJetsZ[1])
	_cosThetaStarZjj_CS_ee_gen = getCosThetaStar_CS(_genJetsZ[0]+_genJetsZ[1], _genElectronsZ[0]+_genElectronsZ[1])
	_cosThetaStarZee_CS = getCosThetaStar_CS(electrons[0]+electrons[1], jet1+jet2)
	_cosThetaStarZjj_CS_ee = getCosThetaStar_CS(jet1+jet2, electrons[0]+electrons[1])

	cosThetaAng_ZZ_ee_gen = CosThetaAngles_ZZ(_genJetsZ[0], _genJetsZ[1], _genElectronsZ[0], _genElectronsZ[1])
	_cosTheta_Zee_gen = cosThetaAng_ZZ_ee_gen[0]
	_cosTheta_Zjj_ee_gen = cosThetaAng_ZZ_ee_gen[1]
	cosThetaAng_ZZ_ee = CosThetaAngles_ZZ(jet1, jet2, electrons[0], electrons[1])
	_cosTheta_Zee = cosThetaAng_ZZ_ee[0]
	_cosTheta_Zjj_ee = cosThetaAng_ZZ_ee[1]

	phiAngles_ZZ_ee_gen = getPhi_ZZ(_genJetsZ[0], _genJetsZ[1], _genElectronsZ[0], _genElectronsZ[1])
	_phi0_zz_ee_gen = phiAngles_ZZ_ee_gen[0]
	_phi1_zee_gen = phiAngles_ZZ_ee_gen[1]
	_phi1_zjj_ee_gen = phiAngles_ZZ_ee_gen[2]
	phiAngles_ZZ_ee = getPhi_ZZ(jet1, jet2, electrons[0], electrons[1])
	_phi0_zz_ee  = phiAngles_ZZ_ee[0]
	_phi1_zee = phiAngles_ZZ_ee[1]
	_phi1_zjj_ee = phiAngles_ZZ_ee[2]
	#### AH ####

	didMuon = False
	_Muu4j_gen,_Mee4j_gen,_Mll4j_gen,_Muu4j_genMatched,_Mee4j_genMatched,_Mll4j_genMatched = 0.,0.,0.,0.,0.,0.
	_Muujj_gen,_Muujj_genMatched,_Meejj_gen,_Meejj_genMatched,_Mlljj_gen,_Mlljj_genMatched, = 0.,0.,0.,0.,0.,0.

	_Muujj_gen = (_genJetsZ[0]+_genJetsZ[1]+_genMuonsZ[0]+_genMuonsZ[1]).M()
	_Muujj_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoMuonsZ[0]+_matchedRecoMuonsZ[1]).M()
	_Meejj_gen = (_genJetsZ[0]+_genJetsZ[1]+_genElectronsZ[0]+_genElectronsZ[1]).M()
	_Meejj_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoElectronsZ[0]+_matchedRecoElectronsZ[1]).M()
	_Mll4j_gen = (_genJetsZ[0]+_genJetsZ[1]+_genJetsH[0]+_genJetsH[1]+_genLeptonsZ[0]+_genLeptonsZ[1]).M()
	_Mll4j_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoJetsH[0]+_matchedRecoJetsH[1]+_matchedRecoLeptonsZ[0]+_matchedRecoLeptonsZ[1]).M()

	#if v == '' : print 'Gen level ZJets:',len(_genJetsZ),'HJets:',len(_genJetsH),'ZMuons:',len(_genMuonsZ),'ZElectrons:',len(_genElectronsZ)
	if  _isMuonEvent:
		if len(_genMuonsZ)>=2: _Muu_gen = (_genMuonsZ[0]+_genMuonsZ[1]).M()
		if len(_genJetsZ)>=2  and len(_genJetsH)>=2 and len(_genMuonsZ)>=2:
			_Muu4j_gen = (_genJetsZ[0]+_genJetsZ[1]+_genJetsH[0]+_genJetsH[1]+_genMuonsZ[0]+_genMuonsZ[1]).M()
			_Mll4j_gen = (_genJetsZ[0]+_genJetsZ[1]+_genJetsH[0]+_genJetsH[1]+_genMuonsZ[0]+_genMuonsZ[1]).M()
		didMuon = True

	if  _isElectronEvent:
		if len(_genElectronsZ)>=2: _Mee_gen = (_genElectronsZ[0]+_genElectronsZ[1]).M()
		if len(_genJetsZ)>=2 and len(_genJetsH)>=2 and len(_genElectronsZ)>=2 and not didMuon :
			_Mee4j_gen = (_genJetsZ[0]+_genJetsZ[1]+_genJetsH[0]+_genJetsH[1]+_genElectronsZ[0]+_genElectronsZ[1]).M()
			_Mll4j_gen = (_genJetsZ[0]+_genJetsZ[1]+_genJetsH[0]+_genJetsH[1]+_genElectronsZ[0]+_genElectronsZ[1]).M()

	if  didMuon:
		if len(_matchedRecoMuonsZ)>=2 : _Muu_genMatched = (_matchedRecoMuonsZ[0]+_matchedRecoMuonsZ[1]).M()
		if len(_matchedRecoJetsZ)>=2 and len(_matchedRecoJetsH)>=2 and len(_matchedRecoMuonsZ)>=2 :
			_Muu4j_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoJetsH[0]+_matchedRecoJetsH[1]+_matchedRecoMuonsZ[0]+_matchedRecoMuonsZ[1]).M()
			_Mll4j_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoJetsH[0]+_matchedRecoJetsH[1]+_matchedRecoMuonsZ[0]+_matchedRecoMuonsZ[1]).M()

	if not didMuon:
		if len(_matchedRecoElectronsZ)>=2 :_Mee_genMatched = (_matchedRecoMuonsZ[0]+_matchedRecoMuonsZ[1]).M()
		if len(_matchedRecoJetsZ)>=2 and len(_matchedRecoJetsH)>=2 and len(_matchedRecoElectronsZ)>=2 :
			_Mee4j_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoJetsH[0]+_matchedRecoJetsH[1]+_matchedRecoElectronsZ[0]+_matchedRecoElectronsZ[1]).M()
			_Mll4j_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]+_matchedRecoJetsH[0]+_matchedRecoJetsH[1]+_matchedRecoElectronsZ[0]+_matchedRecoElectronsZ[1]).M()


	_Mjj_Z_gen, _Mbb_H_gen, _Mjj_Z_genMatched, _Mbb_H_genMatched = 0.,0.,0.,0.
	if len(_genJetsZ)>=2 and len(_genJetsH)>=2 :
		_Mjj_Z_gen = (_genJetsZ[0]+_genJetsZ[1]).M()
		_Mbb_H_gen = (_genJetsH[0]+_genJetsH[1]).M()
		#if v == '' : print '_Mjj_Z_gen',_Mjj_Z_gen,'_Mbb_H_gen',_Mbb_H_gen
	if len(_matchedRecoJetsZ)>=2 and len(_matchedRecoJetsH)>=2 :
		_Mjj_Z_genMatched = (_matchedRecoJetsZ[0]+_matchedRecoJetsZ[1]).M()
		_Mbb_H_genMatched = (_matchedRecoJetsH[0]+_matchedRecoJetsH[1]).M()


	_genjetcount = 0
	if isData==0:
		_genjetcount = T.nGenJet

	_NGenMuonsZ = 0
	_NGenElecsZ = 0
	_NGenMuonsZ = len(_genMuonsZ)
	_NGenElecsZ = len(_genElectronsZ)

	#----- calculate BDT disc here
	#-- muon bdt
	_uu_s0_bdt_discrims = [-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0]
	for kth in range(len(_uu_s0_bdt_discrims)):
		_uu_s0_bdt_discrims[kth] = calculateBDTdiscriminant(reader_22vars_uu, str("BDT_classifier_22vars_s0_uu_M" + SignalM[kth]), _bdtvarnames_uu, _Muu4j, _Mbb_H, _Mjj_Z, _Muu, _Muujj, _ptmu1, _ptmu2, _ptmet, _Pt_Hjet1, _Pt_Hjet2, _Pt_Zjet1, _Pt_Zjet2, _Pt_uu, _Pt_Hjets, _Pt_Zjets, _dRbb_H, _dRjj_Z, _DRuu, _phi0_uu, _phi1_uu, _phi0_zz_uu, _phi1_zuu, _phi1_zjj_uu, bscoreMVA1, bscoreMVA2, _dRu1Hj1, _dRu1Hj2, _dRu2Hj1, _dRu2Hj2, _dRu1Zj1, _dRu1Zj2, _dRu2Zj1, _dRu2Zj2, _dRuubb_H, _dRuujj_Z, _cosThetaStarMu, _cosTheta_hbb_uu, _cosTheta_zuu_hzz, _cosThetaStar_uu, _cosThetaStarZuu_CS, _cosTheta_Zuu, _etamu1, _etamu2, _phimu1, _phimu2, _DPHIuv, _dPHIuujj_Z, _dPHIuubb_H, _dPhibb_H, _dPhijj_Z)
	[_uu_s0_bdt_discrim_M260, _uu_s0_bdt_discrim_M270, _uu_s0_bdt_discrim_M300, _uu_s0_bdt_discrim_M350, _uu_s0_bdt_discrim_M400, _uu_s0_bdt_discrim_M450, _uu_s0_bdt_discrim_M500, _uu_s0_bdt_discrim_M550, _uu_s0_bdt_discrim_M600, _uu_s0_bdt_discrim_M650, _uu_s0_bdt_discrim_M750, _uu_s0_bdt_discrim_M800, _uu_s0_bdt_discrim_M900, _uu_s0_bdt_discrim_M1000] = _uu_s0_bdt_discrims
	#if v == '' : print ' _uu_bdt_discrims ', _uu_bdt_discrims
	#if v == '' : print ' each bdt         ', _uu_bdt_discrim_M260, _uu_bdt_discrim_M270, _uu_bdt_discrim_M300, _uu_bdt_discrim_M350, _uu_bdt_discrim_M400
	_uu_s2_bdt_discrims = [-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0]
	for kth in range(len(_uu_s2_bdt_discrims)):
		_uu_s2_bdt_discrims[kth] = calculateBDTdiscriminant(reader_22vars_uu, str("BDT_classifier_22vars_s2_uu_M" + SignalM[kth]), _bdtvarnames_uu, _Muu4j, _Mbb_H, _Mjj_Z, _Muu, _Muujj, _ptmu1, _ptmu2, _ptmet, _Pt_Hjet1, _Pt_Hjet2, _Pt_Zjet1, _Pt_Zjet2, _Pt_uu, _Pt_Hjets, _Pt_Zjets, _dRbb_H, _dRjj_Z, _DRuu, _phi0_uu, _phi1_uu, _phi0_zz_uu, _phi1_zuu, _phi1_zjj_uu, bscoreMVA1, bscoreMVA2, _dRu1Hj1, _dRu1Hj2, _dRu2Hj1, _dRu2Hj2, _dRu1Zj1, _dRu1Zj2, _dRu2Zj1, _dRu2Zj2, _dRuubb_H, _dRuujj_Z, _cosThetaStarMu, _cosTheta_hbb_uu, _cosTheta_zuu_hzz, _cosThetaStar_uu, _cosThetaStarZuu_CS, _cosTheta_Zuu, _etamu1, _etamu2, _phimu1, _phimu2, _DPHIuv, _dPHIuujj_Z, _dPHIuubb_H, _dPhibb_H, _dPhijj_Z)
	[_uu_s2_bdt_discrim_M260, _uu_s2_bdt_discrim_M270, _uu_s2_bdt_discrim_M300, _uu_s2_bdt_discrim_M350, _uu_s2_bdt_discrim_M400, _uu_s2_bdt_discrim_M450, _uu_s2_bdt_discrim_M500, _uu_s2_bdt_discrim_M550, _uu_s2_bdt_discrim_M600, _uu_s2_bdt_discrim_M650, _uu_s2_bdt_discrim_M750, _uu_s2_bdt_discrim_M800, _uu_s2_bdt_discrim_M900, _uu_s2_bdt_discrim_M1000] = _uu_s2_bdt_discrims

	#-- electron bdt
	_ee_s0_bdt_discrims = [-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0]
	for kth in range(len(_ee_s0_bdt_discrims)):
		_ee_s0_bdt_discrims[kth] = calculateBDTdiscriminant(reader_22vars_ee, str("BDT_classifier_22vars_s0_ee_M" + SignalM[kth]), _bdtvarnames_ee, _Mee4j, _Mbb_H, _Mjj_Z, _Mee, _Meejj, _ptele1, _ptele2, _ptmet, _Pt_Hjet1, _Pt_Hjet2, _Pt_Zjet1, _Pt_Zjet2, _Pt_ee, _Pt_Hjets, _Pt_Zjets, _dRbb_H, _dRjj_Z, _DRee, _phi0_ee, _phi1_ee, _phi0_zz_ee, _phi1_zee, _phi1_zjj_ee, bscoreMVA1, bscoreMVA2, _dRe1Hj1, _dRe1Hj2, _dRe2Hj1, _dRe2Hj2, _dRe1Zj1, _dRe1Zj2, _dRe2Zj1, _dRe2Zj2, _dReebb_H, _dReejj_Z, _cosThetaStarEle, _cosTheta_hbb_ee, _cosTheta_zee_hzz, _cosThetaStar_ee, _cosThetaStarZee_CS, _cosTheta_Zee, _etaele1, _etaele2, _phiele1, _phiele2, _DPHIev, _dPHIeejj_Z, _dPHIeebb_H, _dPhibb_H, _dPhijj_Z)
	[_ee_s0_bdt_discrim_M260, _ee_s0_bdt_discrim_M270, _ee_s0_bdt_discrim_M300, _ee_s0_bdt_discrim_M350, _ee_s0_bdt_discrim_M400, _ee_s0_bdt_discrim_M450, _ee_s0_bdt_discrim_M500, _ee_s0_bdt_discrim_M550, _ee_s0_bdt_discrim_M600, _ee_s0_bdt_discrim_M650, _ee_s0_bdt_discrim_M750, _ee_s0_bdt_discrim_M800, _ee_s0_bdt_discrim_M900, _ee_s0_bdt_discrim_M1000] = _ee_s0_bdt_discrims
	_ee_s2_bdt_discrims = [-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0,-99.0]
	for kth in range(len(_ee_s2_bdt_discrims)):
		_ee_s2_bdt_discrims[kth] = calculateBDTdiscriminant(reader_22vars_ee, str("BDT_classifier_22vars_s2_ee_M" + SignalM[kth]), _bdtvarnames_ee, _Mee4j, _Mbb_H, _Mjj_Z, _Mee, _Meejj, _ptele1, _ptele2, _ptmet, _Pt_Hjet1, _Pt_Hjet2, _Pt_Zjet1, _Pt_Zjet2, _Pt_ee, _Pt_Hjets, _Pt_Zjets, _dRbb_H, _dRjj_Z, _DRee, _phi0_ee, _phi1_ee, _phi0_zz_ee, _phi1_zee, _phi1_zjj_ee, bscoreMVA1, bscoreMVA2, _dRe1Hj1, _dRe1Hj2, _dRe2Hj1, _dRe2Hj2, _dRe1Zj1, _dRe1Zj2, _dRe2Zj1, _dRe2Zj2, _dReebb_H, _dReejj_Z, _cosThetaStarEle, _cosTheta_hbb_ee, _cosTheta_zee_hzz, _cosThetaStar_ee, _cosThetaStarZee_CS, _cosTheta_Zee, _etaele1, _etaele2, _phiele1, _phiele2, _DPHIev, _dPHIeejj_Z, _dPHIeebb_H, _dPhibb_H, _dPhijj_Z)
	[_ee_s2_bdt_discrim_M260, _ee_s2_bdt_discrim_M270, _ee_s2_bdt_discrim_M300, _ee_s2_bdt_discrim_M350, _ee_s2_bdt_discrim_M400, _ee_s2_bdt_discrim_M450, _ee_s2_bdt_discrim_M500, _ee_s2_bdt_discrim_M550, _ee_s2_bdt_discrim_M600, _ee_s2_bdt_discrim_M650, _ee_s2_bdt_discrim_M750, _ee_s2_bdt_discrim_M800, _ee_s2_bdt_discrim_M900, _ee_s2_bdt_discrim_M1000] = _ee_s2_bdt_discrims

	_bdtdiscr = -1.0
	_bdtdiscrZ = -1.0

	(ak8_bdtjetH, ak8_bdtjetZ, _bdtdiscr, _bdtdiscrZ, _bdtjetindH, _bdtjetindZ) = AK8calculateBDTdiscriminant(reader, "BDT_classifier", _bdtvarnames, T,  _ptmu1, _ptmu2, _ak8_ptrecoj1) #ptak8jet1 to make sure there is an ak8 jet in the event

	[_ak8_ptHj]=[ak8_bdtjetH.Pt()]
	[_ak8_massHj]=[ak8_bdtjetH.M()]
	[_ak8_ptZj]=[ak8_bdtjetZ.Pt()]
	[_ak8_massZj]=[ak8_bdtjetZ.M()]

	if _bdtjetindH == _ak8jetInd:
################# kinematics of jets that are selected using bdt and match the genMatched Jet index
		[_ak8_ptHj_Matched]=[ak8_bdtjetH.Pt()] ##################### pt of the genmatched jet
		[_ak8_massHj_Matched]=[ak8_bdtjetH.M()] #################### mass of the genmatched jet
	else:
		[_ak8_ptHj_Matched]=[-99]
		[_ak8_massHj_Matched]=[-99]

	if _bdtjetindZ == _ak8jetZInd:
		[_ak8_ptZj_Matched]=[ak8_bdtjetZ.Pt()]
		[_ak8_massZj_Matched]=[ak8_bdtjetZ.M()]
	else:
		[_ak8_ptZj_Matched]=[-99]
		[_ak8_massZj_Matched]=[-99]

	#----- End calculate BDT disc here

	_ak8_Muu4j = (muons[0]+muons[1]+ak8_bdtjetH+ak8_bdtjetZ).M()
	_ak8_Mee4j = (electrons[0]+electrons[1]+ak8_bdtjetH+ak8_bdtjetZ).M()
	_ak8_Mbb_H = ak8_bdtjetH.M()
	_ak8_Mjj_Z = ak8_bdtjetZ.M()

	_ak8_Mjj_Z_genMatched, _ak8_Mbb_H_genMatched = 0.,0.
	if len(_matchedRecoJetsZ)>=2 and len(_matchedRecoJetsH)>=2 :
		_ak8_Mjj_Z_genMatched = _ak8_massZj_Matched
		_ak8_Mbb_H_genMatched = _ak8_massZj_Matched

	_ak8_dRu1Hj = abs(muons[0].DeltaR(ak8_bdtjetH))
	_ak8_dRu2Hj = abs(muons[1].DeltaR(ak8_bdtjetH))
	_ak8_dRu1Zj = abs(muons[0].DeltaR(ak8_bdtjetZ))
	_ak8_dRu2Zj = abs(muons[1].DeltaR(ak8_bdtjetZ))

	_ak8_dRu1Hj_genMatched = abs(_matchedRecoMuonsZ[0].DeltaR(ak8_matchedRecoJetH[0]))
	_ak8_dRu2Hj_genMatched = abs(_matchedRecoMuonsZ[1].DeltaR(ak8_matchedRecoJetH[0]))
	_ak8_dRu1Zj_genMatched = abs(_matchedRecoMuonsZ[0].DeltaR(ak8_matchedRecoJetZ[0]))
	_ak8_dRu2Zj_genMatched = abs(_matchedRecoMuonsZ[1].DeltaR(ak8_matchedRecoJetZ[0]))

	_ak8_dRe1Hj = abs(electrons[0].DeltaR(ak8_bdtjetH))
	_ak8_dRe2Hj = abs(electrons[1].DeltaR(ak8_bdtjetH))
	_ak8_dRe1Zj = abs(electrons[0].DeltaR(ak8_bdtjetZ))
	_ak8_dRe2Zj = abs(electrons[1].DeltaR(ak8_bdtjetZ))

	_ak8_dRe1Hj_genMatched = abs(_matchedRecoElectronsZ[0].DeltaR(ak8_matchedRecoJetH[0]))
	_ak8_dRe2Hj_genMatched = abs(_matchedRecoElectronsZ[1].DeltaR(ak8_matchedRecoJetH[0]))
	_ak8_dRe1Zj_genMatched = abs(_matchedRecoElectronsZ[0].DeltaR(ak8_matchedRecoJetZ[0]))
	_ak8_dRe2Zj_genMatched = abs(_matchedRecoElectronsZ[1].DeltaR(ak8_matchedRecoJetZ[0]))

	_ak8_dRuubb_H = abs((muons[0]+muons[1]).DeltaR(ak8_bdtjetH))
	_ak8_dRuujj_Z = abs((muons[0]+muons[1]).DeltaR(ak8_bdtjetZ))
	_ak8_dPHIuubb_H = abs((muons[0]+muons[1]).DeltaPhi(ak8_bdtjetH))
	_ak8_dPHIuujj_Z = abs((muons[0]+muons[1]).DeltaPhi(ak8_bdtjetZ))
	_ak8_dReebb_H = abs((electrons[0]+electrons[1]).DeltaR(ak8_bdtjetH))
	_ak8_dReejj_Z = abs((electrons[0]+electrons[1]).DeltaR(ak8_bdtjetZ))
	_ak8_dPHIeebb_H = abs((electrons[0]+electrons[1]).DeltaPhi(ak8_bdtjetH))
	_ak8_dPHIeejj_Z = abs((electrons[0]+electrons[1]).DeltaPhi(ak8_bdtjetZ))

	_ak8_Muu4j_genMatched,_ak8_Mee4j_genMatched = 0.,0.

	if  didMuon:
		if len(_matchedRecoMuonsZ)>=2 :
			_ak8_Muu4j_genMatched = (ak8_matchedRecoJetZ[0]+ak8_matchedRecoJetH[0]+_matchedRecoMuonsZ[0]+_matchedRecoMuonsZ[1]).M()
			_ak8_Mee4j_genMatched = (ak8_matchedRecoJetZ[0]+ak8_matchedRecoJetH[0]+_matchedRecoElectronsZ[0]+_matchedRecoElectronsZ[1]).M()


	# This MUST have the same structure as _kinematic variables!
	toreturn = [_ptmu1,_ptmu2,_ptele1,_ptele2,_ptj1,_ptj2,_ptmet]
	toreturn += [_ptj3,_ptj4]
	toreturn += [_etamu1,_etamu2,_etaele1,_etaele2,_etaj1,_etaj2]
	toreturn += [_phimu1,_phimu2,_phiele1,_phiele2,_phij1,_phij2,_phimet]
	toreturn += [_phiHj1,_phiHj2,_phiZj1,_phiZj2]
	toreturn += [_etaHj1,_etaHj2,_etaZj1,_etaZj2]
	toreturn += [_ptu1_gen,_ptu2_gen]
	toreturn += [_ptHj1_gen,_ptHj2_gen,_ptZj1_gen,_ptZj2_gen]
	toreturn += [_phiHj1_gen,_phiHj2_gen,_phiZj1_gen,_phiZj2_gen]
	toreturn += [_etaHj1_gen,_etaHj2_gen,_etaZj1_gen,_etaZj2_gen]
	toreturn += [_ptu1_genMatched,_ptu2_genMatched]
	toreturn += [_ptHj1_genMatched,_ptHj2_genMatched,_ptZj1_genMatched,_ptZj2_genMatched]

	toreturn += [_ak8_ptrecoj1]
	toreturn += [_ak8_ptHj_genMatched,_ak8_ptZj_genMatched]
	toreturn += [_ak8_etaHj_genMatched,_ak8_etaZj_genMatched]
	toreturn += [_ak8_phiHj_genMatched,_ak8_phiZj_genMatched]
	toreturn += [_ak8_massHj_genMatched,_ak8_massZj_genMatched]
	toreturn += [_ak8_drujH_genMatched,_ak8_drujZ_genMatched,_ak8_drujH_gen,_ak8_drujZ_gen]
	toreturn += [_ak8_csvHj_genMatched,_ak8_csvZj_genMatched]
	toreturn += [_bdtdiscr,_bdtdiscrZ]
	toreturn += [_ak8_ptHj,_ak8_ptZj,_ak8_massHj,_ak8_massZj]
	toreturn += [_ak8_ptHj_Matched,_ak8_ptZj_Matched,_ak8_massHj_Matched,_ak8_massZj_Matched]
	toreturn += [_ak8_Muu4j,_ak8_Mee4j]
	toreturn += [_ak8_Mbb_H,_ak8_Mjj_Z]
	toreturn += [_ak8_Mbb_H_genMatched,_ak8_Mjj_Z_genMatched]
	toreturn += [_ak8_dRu1Hj,_ak8_dRu2Hj]
	toreturn += [_ak8_dRu1Zj,_ak8_dRu2Zj]
	toreturn += [_ak8_dRu1Hj_genMatched,_ak8_dRu2Hj_genMatched]
	toreturn += [_ak8_dRu1Zj_genMatched,_ak8_dRu2Zj_genMatched]
	toreturn += [_ak8_dRe1Hj,_ak8_dRe2Hj]
	toreturn += [_ak8_dRe1Zj,_ak8_dRe2Zj]
	toreturn += [_ak8_dRe1Hj_genMatched,_ak8_dRe2Hj_genMatched]
	toreturn += [_ak8_dRe1Zj_genMatched,_ak8_dRe2Zj_genMatched]
	toreturn += [_ak8_dRuubb_H,_ak8_dRuujj_Z,_ak8_dPHIuubb_H,_ak8_dPHIuujj_Z]
	toreturn += [_ak8_dReebb_H,_ak8_dReejj_Z,_ak8_dPHIeebb_H,_ak8_dPHIeejj_Z]
	toreturn += [_ak8_Muu4j_genMatched]
	toreturn += [_ak8_Mee4j_genMatched]

	toreturn += [_xmiss,_ymiss]
	toreturn += [_isomu1,_isomu2,_isoele1,_isoele2]
	toreturn += [_qmu1,_qmu2,_qele1,_qele2]
	toreturn += [_dptmu1,_dptmu2]
	toreturn += [_stuu4j,_stee4j]
	toreturn += [_Muu,_Mee]
	toreturn += [_Mjj]
	toreturn += [_DRuu,_DPHIuv]#,_DPHIj1v,_DPHIj2v]
	toreturn += [_DRee,_DPHIev]
	toreturn += [_Muujj, _Meejj]
	toreturn += [_Muu4j, _Mee4j]
	toreturn += [_Mbb_H,_Mjj_Z,_Mjj_Z_3jet]
	toreturn += [_Mbb_H_gen,_Mjj_Z_gen]
	toreturn += [_Mbb_H_genMatched,_Mjj_Z_genMatched]
	toreturn += [_Mbb_H_orig,_Muu4j_orig]
	toreturn += [_cosThetaStarMu,_cosThetaStarEle]
	toreturn += [_cosThetaStarMu_gen,_cosThetaStarEle_gen]
	toreturn += [_cosThetaStar_uu_gen,_cosTheta_hbb_uu_gen,_cosTheta_zjj_hzz_uu_gen,_cosTheta_zuu_hzz_gen,_cosTheta_zj1_hzz_uu_gen,_cosTheta_zu1_hzz_gen]
	toreturn += [_cosThetaStar_ee_gen,_cosTheta_hbb_ee_gen,_cosTheta_zjj_hzz_ee_gen,_cosTheta_zee_hzz_gen,_cosTheta_zj1_hzz_ee_gen,_cosTheta_ze1_hzz_gen]
	toreturn += [_phi0_uu_gen, _phi1_uu_gen]
	toreturn += [_phi0_ee_gen, _phi1_ee_gen]
	toreturn += [_cosThetaStarZuu_CS_gen, _cosTheta_Zuu_gen]
	toreturn += [_cosThetaStarZee_CS_gen, _cosTheta_Zee_gen]
	toreturn += [_phi0_zz_uu_gen, _phi1_zuu_gen, _phi1_zjj_uu_gen]
	toreturn += [_phi0_zz_ee_gen, _phi1_zee_gen, _phi1_zjj_ee_gen]
	toreturn += [_cosThetaStar_uu,_cosTheta_hbb_uu,_cosTheta_zjj_hzz_uu,_cosTheta_zuu_hzz,_cosTheta_zj1_hzz_uu,_cosTheta_zu1_hzz]
	toreturn += [_cosThetaStar_ee,_cosTheta_hbb_ee,_cosTheta_zjj_hzz_ee,_cosTheta_zee_hzz,_cosTheta_zj1_hzz_ee,_cosTheta_ze1_hzz]
	toreturn += [_phi0_uu, _phi1_uu]
	toreturn += [_phi0_ee, _phi1_ee]
	toreturn += [_cosThetaStarZuu_CS, _cosTheta_Zuu]
	toreturn += [_cosThetaStarZee_CS, _cosTheta_Zee]
	toreturn += [_phi0_zz_uu, _phi1_zuu, _phi1_zjj_uu]
	toreturn += [_phi0_zz_ee, _phi1_zee, _phi1_zjj_ee]
	toreturn += [_Pt_origHjet1,_Pt_origHjet2]
	toreturn += [_Pt_Hjet1,_Pt_Hjet2,_Pt_Zjet1,_Pt_Zjet2]
	toreturn += [_Pt_Hjets,_Pt_Zjets,_Pt_uu,_Pt_ee]
	toreturn += [_dRjj_Z,_dRbb_H]
	toreturn += [_dRu1Hj1,_dRu1Hj2,_dRu2Hj1,_dRu2Hj2]
	toreturn += [_dRu1Zj1,_dRu1Zj2,_dRu2Zj1,_dRu2Zj2]
	toreturn += [_dRu1Hj1_gen,_dRu1Hj2_gen,_dRu2Hj1_gen,_dRu2Hj2_gen]
	toreturn += [_dRu1Zj1_gen,_dRu1Zj2_gen,_dRu2Zj1_gen,_dRu2Zj2_gen]
	toreturn += [_dRu1Hj1_genMatched,_dRu1Hj2_genMatched,_dRu2Hj1_genMatched,_dRu2Hj2_genMatched]
	toreturn += [_dRu1Zj1_genMatched,_dRu1Zj2_genMatched,_dRu2Zj1_genMatched,_dRu2Zj2_genMatched]
	toreturn += [_dRe1Hj1,_dRe1Hj2,_dRe2Hj1,_dRe2Hj2]
	toreturn += [_dRe1Zj1,_dRe1Zj2,_dRe2Zj1,_dRe2Zj2]
	toreturn += [_dRe1Hj1_gen,_dRe1Hj2_gen,_dRe2Hj1_gen,_dRe2Hj2_gen]
	toreturn += [_dRe1Zj1_gen,_dRe1Zj2_gen,_dRe2Zj1_gen,_dRe2Zj2_gen]
	toreturn += [_dRe1Hj1_genMatched,_dRe1Hj2_genMatched,_dRe2Hj1_genMatched,_dRe2Hj2_genMatched]
	toreturn += [_dRe1Zj1_genMatched,_dRe1Zj2_genMatched,_dRe2Zj1_genMatched,_dRe2Zj2_genMatched]
	toreturn += [_dRuubb_H,_dRuujj_Z,_dPHIuubb_H,_dPHIuujj_Z]
	toreturn += [_dReebb_H,_dReejj_Z,_dPHIeebb_H,_dPHIeejj_Z]
	toreturn += [_dPhijj_Z,_dPhibb_H]
	toreturn += [_Muu4j_gen,_Muu4j_genMatched]
	toreturn += [_Mee4j_gen,_Mee4j_genMatched]
	toreturn += [_jetCntPreFilter,_jetcount,_mucount,_elcount,_genjetcount]
	toreturn += [_muonInd1,_muonInd2]
	toreturn += [_ptHat]
	toreturn += [_cmva_Zjet1,_cmva_Zjet2]
	toreturn += [bscoreMVA1,bscoreMVA2]
	toreturn += [_Hjet1BsfLoose,_Hjet1BsfLooseUp,_Hjet1BsfLooseDown]
	toreturn += [_Hjet1BsfMedium,_Hjet1BsfMediumUp,_Hjet1BsfMediumDown]
	toreturn += [_Hjet2BsfLoose,_Hjet2BsfLooseUp,_Hjet2BsfLooseDown]
	toreturn += [_Hjet2BsfMedium,_Hjet2BsfMediumUp,_Hjet2BsfMediumDown]
	toreturn += [_Zjet1BsfLoose,_Zjet1BsfLooseUp,_Zjet1BsfLooseDown]
	toreturn += [_Zjet1BsfMedium,_Zjet1BsfMediumUp,_Zjet1BsfMediumDown]
	toreturn += [_Zjet2BsfLoose,_Zjet2BsfLooseUp,_Zjet2BsfLooseDown]
	toreturn += [_Zjet2BsfMedium,_Zjet2BsfMediumUp,_Zjet2BsfMediumDown]
	toreturn += [_ele1IDandIsoSF,_ele2IDandIsoSF]
	toreturn += [_ele1IDandIsoSFup,_ele2IDandIsoSFup]
	toreturn += [_ele1IDandIsoSFdown,_ele2IDandIsoSFdown]
	toreturn += [_ele1hltSF,_ele1hltSFup,_ele1hltSFdown]
	toreturn += [_ele2hltSF,_ele2hltSFup,_ele2hltSFdown]
	toreturn += [_isMuonEvent,_isElectronEvent]
	toreturn += [_isElectronEvent_gen,_isMuonEvent_gen,_isTauEvent_gen]
	toreturn += [_Hj1Matched,_Hj2Matched,_Zj1Matched,_Zj2Matched]
	toreturn += [_Hj1Present,_Hj2Present,_Zj1Present,_Zj2Present]
	toreturn += [_NGenMuonsZ, _NGenElecsZ]
	toreturn += [_Muujj_gen, _Muujj_genMatched]
	toreturn += [_Meejj_gen, _Meejj_genMatched]
	toreturn += [_Muu_gen, _Muu_genMatched]
	toreturn += [_Mee_gen, _Mee_genMatched]
	toreturn += [_bscoreMVA1_genMatched, _bscoreMVA2_genMatched]
	toreturn += [_CorHj1j2Avail,_CorZj1j2Avail]
	toreturn += [_WorZSystemPt]

	toreturn += [_uu_s0_bdt_discrim_M260,_uu_s0_bdt_discrim_M270,_uu_s0_bdt_discrim_M300,_uu_s0_bdt_discrim_M350,_uu_s0_bdt_discrim_M400]
	toreturn += [_uu_s0_bdt_discrim_M450,_uu_s0_bdt_discrim_M500,_uu_s0_bdt_discrim_M550,_uu_s0_bdt_discrim_M600,_uu_s0_bdt_discrim_M650]
	toreturn += [_uu_s0_bdt_discrim_M750,_uu_s0_bdt_discrim_M800,_uu_s0_bdt_discrim_M900,_uu_s0_bdt_discrim_M1000]
	toreturn += [_ee_s0_bdt_discrim_M260,_ee_s0_bdt_discrim_M270,_ee_s0_bdt_discrim_M300,_ee_s0_bdt_discrim_M350,_ee_s0_bdt_discrim_M400]
	toreturn += [_ee_s0_bdt_discrim_M450,_ee_s0_bdt_discrim_M500,_ee_s0_bdt_discrim_M550,_ee_s0_bdt_discrim_M600,_ee_s0_bdt_discrim_M650]
	toreturn += [_ee_s0_bdt_discrim_M750,_ee_s0_bdt_discrim_M800,_ee_s0_bdt_discrim_M900,_ee_s0_bdt_discrim_M1000]
	toreturn += [_uu_s2_bdt_discrim_M260,_uu_s2_bdt_discrim_M270,_uu_s2_bdt_discrim_M300,_uu_s2_bdt_discrim_M350,_uu_s2_bdt_discrim_M400]
	toreturn += [_uu_s2_bdt_discrim_M450,_uu_s2_bdt_discrim_M500,_uu_s2_bdt_discrim_M550,_uu_s2_bdt_discrim_M600,_uu_s2_bdt_discrim_M650]
	toreturn += [_uu_s2_bdt_discrim_M750,_uu_s2_bdt_discrim_M800,_uu_s2_bdt_discrim_M900,_uu_s2_bdt_discrim_M1000]
	toreturn += [_ee_s2_bdt_discrim_M260,_ee_s2_bdt_discrim_M270,_ee_s2_bdt_discrim_M300,_ee_s2_bdt_discrim_M350,_ee_s2_bdt_discrim_M400]
	toreturn += [_ee_s2_bdt_discrim_M450,_ee_s2_bdt_discrim_M500,_ee_s2_bdt_discrim_M550,_ee_s2_bdt_discrim_M600,_ee_s2_bdt_discrim_M650]
	toreturn += [_ee_s2_bdt_discrim_M750,_ee_s2_bdt_discrim_M800,_ee_s2_bdt_discrim_M900,_ee_s2_bdt_discrim_M1000]

	toreturn_systOnly = [_uu_s0_bdt_discrim_M260,_uu_s0_bdt_discrim_M270,_uu_s0_bdt_discrim_M300,_uu_s0_bdt_discrim_M350,_uu_s0_bdt_discrim_M400]
	toreturn_systOnly += [_uu_s0_bdt_discrim_M450,_uu_s0_bdt_discrim_M500,_uu_s0_bdt_discrim_M550,_uu_s0_bdt_discrim_M600,_uu_s0_bdt_discrim_M650]
	toreturn_systOnly += [_uu_s0_bdt_discrim_M750,_uu_s0_bdt_discrim_M800,_uu_s0_bdt_discrim_M900,_uu_s0_bdt_discrim_M1000]
	toreturn_systOnly += [_ee_s0_bdt_discrim_M260,_ee_s0_bdt_discrim_M270,_ee_s0_bdt_discrim_M300,_ee_s0_bdt_discrim_M350,_ee_s0_bdt_discrim_M400]
	toreturn_systOnly += [_ee_s0_bdt_discrim_M450,_ee_s0_bdt_discrim_M500,_ee_s0_bdt_discrim_M550,_ee_s0_bdt_discrim_M600,_ee_s0_bdt_discrim_M650]
	toreturn_systOnly += [_ee_s0_bdt_discrim_M750,_ee_s0_bdt_discrim_M800,_ee_s0_bdt_discrim_M900,_ee_s0_bdt_discrim_M1000]
	toreturn_systOnly += [_uu_s2_bdt_discrim_M260,_uu_s2_bdt_discrim_M270,_uu_s2_bdt_discrim_M300,_uu_s2_bdt_discrim_M350,_uu_s2_bdt_discrim_M400]
	toreturn_systOnly += [_uu_s2_bdt_discrim_M450,_uu_s2_bdt_discrim_M500,_uu_s2_bdt_discrim_M550,_uu_s2_bdt_discrim_M600,_uu_s2_bdt_discrim_M650]
	toreturn_systOnly += [_uu_s2_bdt_discrim_M750,_uu_s2_bdt_discrim_M800,_uu_s2_bdt_discrim_M900,_uu_s2_bdt_discrim_M1000]
	toreturn_systOnly += [_ee_s2_bdt_discrim_M260,_ee_s2_bdt_discrim_M270,_ee_s2_bdt_discrim_M300,_ee_s2_bdt_discrim_M350,_ee_s2_bdt_discrim_M400]
	toreturn_systOnly += [_ee_s2_bdt_discrim_M450,_ee_s2_bdt_discrim_M500,_ee_s2_bdt_discrim_M550,_ee_s2_bdt_discrim_M600,_ee_s2_bdt_discrim_M650]
	toreturn_systOnly += [_ee_s2_bdt_discrim_M750,_ee_s2_bdt_discrim_M800,_ee_s2_bdt_discrim_M900,_ee_s2_bdt_discrim_M1000]

	if v=='': return toreturn
	else: return toreturn_systOnly

def checkWorZpt(T,lowcut, highcut, WorZ):
	#print 'New event'
	maxPt=0.
	for n in range(len(T.GenParticlePdgId)):
		pdg = T.GenParticlePdgId[n]
		status = T.GenParticleStatus[n]
		pt = T.GenParticlePt[n]
		parts = []
		if WorZ=='W' : parts = [-24,24]
		if WorZ=='Z' : parts = [-22,-23,22,23]
		if pdg in parts:#[-24,24]:#23=Z, 24=W, 22=gamma
			#print n,pdg,pt,status
			if pt>maxPt: maxPt=pt
		#	#print n,pdg,pt,status
		#	if pt<100: return 1
		#	else: return 0
		else: continue
	if maxPt<highcut:
		#print 'less than 100!'
		return 1
	else:
		#print 'more than 100!'
		return 0
	return 1

def GeomFilterCollection(collection_to_clean,good_collection,dRcut,associatedCollection1,associatedCollection2,associatedCollection3,associatedCollection4,associatedCollection5,associatedCollection6,associatedCollection7,associatedCollection8):
	# Purpose: Take a collection of TLorentzVectors that you want to clean (arg 1)
	#         by removing all objects within dR of dRcut (arg 3) of any element in
	#         the collection of other particles (arg 2)
	#         e.g.  argumments (jets,muons,0.3) gets rid of jets within 0.3 of muons.
	#   Added option for associated collection, i.e.
	output_collection = []
	associated_output_collection1,associated_output_collection2,associated_output_collection3 = [],[],[]
	associated_output_collection4,associated_output_collection5,associated_output_collection6 = [],[],[]
	associated_output_collection7,associated_output_collection8 = [],[]
	for i, c in enumerate(collection_to_clean):
		isgood = True
		for g in good_collection:
			if (c.DeltaR(g))<dRcut:
				isgood = False
		if isgood==True:
			output_collection.append(c)
			associated_output_collection1.append(associatedCollection1[i])
			associated_output_collection2.append(associatedCollection2[i])
			associated_output_collection3.append(associatedCollection3[i])
			associated_output_collection4.append(associatedCollection4[i])
			associated_output_collection5.append(associatedCollection5[i])
			associated_output_collection6.append(associatedCollection6[i])
			associated_output_collection7.append(associatedCollection7[i])
			associated_output_collection8.append(associatedCollection8[i])
	return [output_collection,associated_output_collection1,associated_output_collection2,associated_output_collection3,associated_output_collection4,associated_output_collection5,associated_output_collection6,associated_output_collection7,associated_output_collection8]


def MetVector(T):
	# Purpose: Creates a TLorentzVector represting the MET. No pseudorapidity, obviously.
	met = TLorentzVector()
	met.SetPtEtaPhiM(T.MET_pt,0,T.MET_phi,0)
	return met

##########################################################################################
#################    BELOW IS THE ACTUAL LOOP OVER ENTRIES         #######################
##########################################################################################
startTime = datetime.now()

# Please don't edit here. It is static. The kinematic calulations are the only thing to edit!
#lumisection = array.array("L",[0])
#t.SetBranchAddress("ls",lumisection)
for n in range(N):
	# This is the loop over events. Due to the heavy use of functions and automation of
	# systematic variations, this loop is very small. It should not really be editted,
	# except possibly to add a new flag or weight variable.
	# All editable contents concerning kinematics are in the function defs.

	# Get the entry
	t.GetEntry(n)
	# if n > 1000:  # Testing....
	# 	break
	if n%100==0:
		print 'Processing event',n, 'of', N # where we are in the loop...

	isData = t.run>1

	## ===========================  BASIC SETUP  ============================= ##
	# print '-----'
	# Assign Weights
	if 'SingleMuon' in name or 'SingleElectron' in name or 'DoubleMuon' in name or 'DoubleEG' in name:
		Branches['weight_central'][0] = 1.0#startingweight*t.genWeight*t.puWeight#GetPUWeight(t,'Central','Basic')
		Branches['weight_pu_down'][0] = 1.0#startingweight*t.genWeight*t.puWeightUp#GetPUWeight(t,'SysDown','Basic')
		Branches['weight_pu_up'][0] = 1.0#startingweight*t.genWeight*t.puWeightDown#GetPUWeight(t,'SysUp','Basic')
		#Branches['weight_central_2012D'][0] = startingweight*GetPUWeight(t,'Central','2012D')
		Branches['weight_nopu'][0] = 1.0#startingweight*t.genWeight
		Branches['weight_topPt'][0]= 1.0#_TopPtFactor*startingweight*t.genWeight
	else:
		Branches['weight_central'][0] = startingweight*t.genWeight*t.puWeight#GetPUWeight(t,'Central','Basic')
		Branches['weight_pu_down'][0] = startingweight*t.genWeight*t.puWeightUp#GetPUWeight(t,'SysDown','Basic')
		Branches['weight_pu_up'][0] = startingweight*t.genWeight*t.puWeightDown#GetPUWeight(t,'SysUp','Basic')
		#Branches['weight_central_2012D'][0] = startingweight*GetPUWeight(t,'Central','2012D')
		Branches['weight_nopu'][0] = startingweight*t.genWeight
		Branches['weight_topPt'][0]=_TopPtFactor*startingweight*t.genWeight

	#if 'amcatnlo' in amcNLOname :
	#	Branches['weight_central'][0]*=t.amcNLOWeight
	#	Branches['weight_pu_down'][0]*=t.amcNLOWeight
	#	Branches['weight_pu_up'][0]*=t.amcNLOWeight
	#	#Branches['weight_central_2012D'][0]*=t.amcNLOWeight
	#	Branches['weight_nopu'][0]*=t.amcNLOWeight
	#Branches['weight_amcNLO'][0]=0#t.amcNLOWeight

	#if 'amcatnlo' in amcNLOname :
	#	scaleWeights = t.ScaleWeightsAMCNLO
	#else:
	#	scaleWeights = t.ScaleWeights
	scaleWeights = [0,0,0,0,0,0,0,0,0]#fixme have to calculate?
	if len(scaleWeights) > 7 :
		Branches['scaleWeight_Up'][0]=       scaleWeights[8]
		Branches['scaleWeight_Down'][0]=     scaleWeights[0]
		Branches['scaleWeight_R0p5_F0p5'][0]=scaleWeights[0]
		Branches['scaleWeight_R0p5_F1'][0]=  scaleWeights[1]
		Branches['scaleWeight_R0p5_F2'][0]=  scaleWeights[2]
		Branches['scaleWeight_R1_F0p5'][0]=  scaleWeights[3]
		Branches['scaleWeight_R1_F1'][0]=    scaleWeights[4]
		Branches['scaleWeight_R1_F2'][0]=    scaleWeights[5]
		Branches['scaleWeight_R2_F0p5'][0]=  scaleWeights[6]
		Branches['scaleWeight_R2_F1'][0]=    scaleWeights[7]
		Branches['scaleWeight_R2_F2'][0]=    scaleWeights[8]
	else :
		Branches['scaleWeight_Up'][0]=       1.0
		Branches['scaleWeight_Down'][0]=     1.0
		Branches['scaleWeight_R1_F1'][0]=    1.0
		Branches['scaleWeight_R1_F2'][0]=    1.0
		Branches['scaleWeight_R1_F0p5'][0]=  1.0
		Branches['scaleWeight_R2_F1'][0]=    1.0
		Branches['scaleWeight_R2_F2'][0]=    1.0
		Branches['scaleWeight_R2_F0p5'][0]=  1.0
		Branches['scaleWeight_R0p5_F1'][0]=  1.0
		Branches['scaleWeight_R0p5_F2'][0]=  1.0
		Branches['scaleWeight_R0p5_F0p5'][0]=1.0

        Branches['prefireWeight'][0]      = t.PrefireWeight
        Branches['prefireWeight_up'][0]   = t.PrefireWeight_Up
        Branches['prefireWeight_down'][0] = t.PrefireWeight_Down

	if isData:
		dopdf = False
	if dopdf:
		pdfweights = GetPDFWeights(t)
		#if len(pdfweights)==len(_pdfweightsnames) :#fixme put in check that there are the same number of weights as weight names - update when all pdf weights work again
		for p in range(len(pdfweights)):
			Branches[_pdfweightsnames[p]][0] = pdfweights[p]

	# Event Flags
	Branches['run_number'][0]   = t.run
	# event_number[0] = int(t.event)
	Branches['event_number'][0] = t.event#fixme todo this is failing for some event in CMSSW_7_1_14
	Branches['lumi_number'][0]  = t.luminosityBlock
	Branches['GoodVertexCount'][0] = t.PV_npvsGood
	Branches['passTriggerObjectMatching'][0] = 0

        #Trigger on Data and MC
	Branches['Flag_HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ'][0] = t.HLT_Ele23_Ele12_CaloIdL_TrackIdL_IsoVL_DZ
	Branches['pass_HLT_Mu17_Mu8'][0] = 1 if (t.HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ + t.HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL)>0 else 0

	if isData:
        	Branches['Flag_BadChargedCandidateFilter'][0]         = t.Flag_BadChargedCandidateFilter
		Branches['Flag_BadGlobalMuon'][0]	       	      = 1#t.Flag_BadGlobalMuon
		Branches['Flag_BadPFMuonFilter'][0]	       	      = t.Flag_BadPFMuonFilter
	else:
                if _year=='2016':
                        Branches['Flag_BadChargedCandidateFilter'][0]         = ord(t.Flag_BadChargedCandidateFilter)
                        Branches['Flag_BadGlobalMuon'][0]	       	      = ord(t.Flag_BadGlobalMuon)	
                        Branches['Flag_BadPFMuonFilter'][0]	       	      = ord(t.Flag_BadPFMuonFilter)
                elif _year=='2017':
                        Branches['Flag_BadChargedCandidateFilter'][0]         = t.Flag_BadChargedCandidateFilter
                        Branches['Flag_BadGlobalMuon'][0]	       	      = 1#t.Flag_BadGlobalMuon		
                        Branches['Flag_BadPFMuonFilter'][0]	       	      = t.Flag_BadPFMuonFilter
	Branches['Flag_BadChargedCandidateSummer16Filter'][0] = 1#t.Flag_BadChargedCandidateSummer16Filter
	Branches['Flag_BadPFMuonSummer16Filter'][0]    	      = 1#t.Flag_BadPFMuonSummer16Filter
	Branches['Flag_CSCTightHalo2015Filter'][0]     	      = t.Flag_CSCTightHalo2015Filter
	Branches['Flag_CSCTightHaloFilter'][0]         	      = t.Flag_CSCTightHaloFilter
	Branches['Flag_CSCTightHaloTrkMuUnvetoFilter'][0]     = t.Flag_CSCTightHaloTrkMuUnvetoFilter
	Branches['Flag_EcalDeadCellBoundaryEnergyFilter'][0]  = t.Flag_EcalDeadCellBoundaryEnergyFilter
	Branches['Flag_EcalDeadCellTriggerPrimitiveFilter'][0]= t.Flag_EcalDeadCellTriggerPrimitiveFilter
	Branches['Flag_HBHENoiseFilter'][0]	       	      = t.Flag_HBHENoiseFilter
	Branches['Flag_HBHENoiseIsoFilter'][0]                = t.Flag_HBHENoiseIsoFilter
	Branches['Flag_HcalStripHaloFilter'][0]               = t.Flag_HcalStripHaloFilter
	Branches['Flag_METFilters'][0]     	              = t.Flag_METFilters
	Branches['Flag_chargedHadronTrackResolutionFilter'][0]= t.Flag_chargedHadronTrackResolutionFilter
	Branches['Flag_ecalBadCalibFilter'][0]                = 1#t.Flag_ecalBadCalibFilter
	Branches['Flag_ecalBadCalibFilterV2'][0]              = 1#t.Flag_ecalBadCalibFilterV2
	Branches['Flag_ecalLaserCorrFilter'][0]               = t.Flag_ecalLaserCorrFilter
	Branches['Flag_eeBadScFilter'][0]  	       	      = t.Flag_eeBadScFilter
	Branches['Flag_globalSuperTightHalo2016Filter'][0]    = t.Flag_globalSuperTightHalo2016Filter
	Branches['Flag_globalTightHalo2016Filter'][0]	      = t.Flag_globalTightHalo2016Filter
	Branches['Flag_goodVertices'][0]		      = t.Flag_goodVertices
	Branches['Flag_hcalLaserEventFilter'][0]     	      = t.Flag_hcalLaserEventFilter
	Branches['Flag_muonBadTrackFilter'][0]       	      = t.Flag_muonBadTrackFilter
	Branches['Flag_trkPOGFilters'][0] 		      = t.Flag_trkPOGFilters
	Branches['Flag_trkPOG_logErrorTooManyClusters'][0]    = t.Flag_trkPOG_logErrorTooManyClusters
	Branches['Flag_trkPOG_manystripclus53X'][0] 	      = t.Flag_trkPOG_manystripclus53X
	Branches['Flag_trkPOG_toomanystripclus53X'][0]        = t.Flag_trkPOG_toomanystripclus53X

	Branches['passDataCert'][0] = 1
	if ( (isData) and (CheckRunLumiCert(t.run,t.luminosityBlock) == False) ) :
		Branches['passDataCert'][0] = 0


	## ===========================  Calculate everything!  ============================= ##

	# Looping over systematic variations
	for v in _variations:
		# All calculations are done here
		calculations = FullKinematicCalculation(t,v)
		# Now cleverly cast the variables
		#for b in range(len(_kinematicvariables)):
		#	Branches[_kinematicvariables[b]+v][0] = calculations[b]
		if v=='':
		        for b in range(len(_kinematicvariables)):
			        Branches[_kinematicvariables[b]][0] = calculations[b]
		else:
			for b in range(len(_kinematicvariables_systOnly)):
				Branches[_kinematicvariables_systOnly[b]+v][0] = calculations[b]

	## ===========================     Skim out events     ============================= ##

	# Feel like skimming? Do it here. The syntax is just Branches[branchname] > blah, or whatever condition
	# you want to impose. This Branches[blah] mapping was needed because branches must be linked to arrays of length [0]
	# BE MINDFUL: Just because the central (non-systematic) quantity meets the skim, does not mean
	# that the systematic varied quantity will, and that will throw off systematics calculations later.
	# Make sure your skim is looser than any selection you will need afterward!

	#if (Branches['Pt_lep1'][0] < 16) : continue
	#if (Branches['Pt_lep2'][0] < 8) : continue
	#if (Branches['Pt_muon1'][0] < 16) and (Branches['Pt_ele1'][0] < 16) : continue
	#if (Branches['Pt_muon1'][0] < 16) and (Branches['Pt_ele1'][0] > 16) and (Branches['Pt_ele2'][0]  < 8): continue
	#if (Branches['Pt_muon1'][0] > 16) and (Branches['Pt_muon2'][0] < 8) and (Branches['Pt_ele1'][0] < 16 or Branches['Pt_ele2'][0]  < 8): continue
	if ((Branches['isMuonEvent'][0]==True) and (Branches['isElectronEvent'][0]==False) and ((Branches['Pt_muon1'][0] < 16) or (Branches['Pt_muon2'][0] < 8) or (Branches['M_uu'][0] < 12))): continue
	if ((Branches['isElectronEvent'][0]==True) and (Branches['isMuonEvent'][0]==False) and ((Branches['Pt_ele1'][0] < 21) or (Branches['Pt_ele2'][0] < 12) or (Branches['M_ee'][0] < 12))): continue
	if ((Branches['isMuonEvent'][0]==False) and (Branches['isElectronEvent'][0]==False)): continue
	#if ((Branches['isMuonEvent'][0]==False)) : continue
	#print 'NGenMuonsZ', Branches['NGenMuonsZ'][0], 'NGenElecsZ', Branches['NGenElecsZ'][0]
	#if (Branches['Pt_muon1'][0] < 16) : continue
	#if (Branches['Pt_muon2'][0] < 8) : continue
	#if (Branches['NGenMuonsZ'][0] < 2) : continue

	#if nonisoswitch != True:
	#		if (Branches['Pt_muon2'][0] < 45) and (Branches['Pt_miss'][0] < 45): continue
	if (Branches['Pt_Hjet1'][0] <  18): continue
	if (Branches['Pt_Hjet2'][0] <  18): continue
	if (Branches['Pt_Zjet1'][0] <  18): continue
	if (Branches['Pt_Zjet2'][0] <  18): continue
	#

	if ((Branches['CMVA_bjet1'][0] < -0.5884) and (Branches['CMVA_bjet2'][0] < -0.5884) and (Branches['CMVA_Zjet1'][0] < -0.5884) and (Branches['CMVA_Zjet1'][0] < -0.5884)): continue

	#if (Branches['St_uujj'][0] < 260) and (Branches['St_uvjj'][0] < 260): continue
	#if (Branches['M_uu'][0]    <  45) and (Branches['MT_uv'][0]   <  45): continue

	# Fill output tree with event
	tout.Fill()

# All done. Write and close file.
tout.Write()
fout.Close()

# Timing, for debugging and optimization
print(datetime.now()-startTime)

import os
print ('mv '+tmpfout+' '+finalfout)
os.system('mv '+tmpfout+' '+finalfout)
#os.system('rm '+junkfile1)
#os.system('rm '+junkfile2)
