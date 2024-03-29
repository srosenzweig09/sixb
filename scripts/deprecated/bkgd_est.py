"""
Author: Suzanne Rosenzweig
"""

with6jNN = False
print(f"with6jNN = {with6jNN}")

from utils.analysis import Tree, Signal
from utils.plotter import Hist
from utils.varUtils import *
from utils.fileUtils.sr import NMSSM_List, JetHT_Data_UL
from utils.fileUtils.misc import DataCards_dir, buildDataCard

from array import array
import awkward as ak
from colorama import Fore, Style
import ROOT
ROOT.gROOT.SetBatch(True)
from terminaltables import AsciiTable
import vector

def getKey(tree, key):
    return tree.get('t6_jet_' + key)

def Print(line):
    if isinstance(line, str): print(Fore.CYAN + line + Style.RESET_ALL)
    else: print(Fore.CYAN + str(line) + Style.RESET_ALL)

nEvents = [
    ['', 'SR', 'VR', 'CR']
]

nBreakdown = [
    ['', 'SR hs', 'SR ls', 'VR hs', 'VR ls', 'CR hs', 'CR ls']
]

# Threshold Parameters
# 6-jet NN threshold
if with6jNN: cut_6jNN = 0.8
else: cut_6jNN = 0

# b-tag sum threshold
btag_sum_cut = 0.68

# edges of mH windows
SR_edge = 25 # GeV
VR_edge = 60 # GeV
CR_edge = 120 # GeV

print(f"SR within {SR_edge} GeV")
print(f"VR within {VR_edge} GeV")
print(f"CR within {CR_edge} GeV")

Print("Processing data...")

# Data Tree Handling
datTree = Tree(JetHT_Data_UL)
datHiggsId = datTree.t6_jet_higgsIdx

print("Generating mX...")
H1_b1 = vector.obj(
    pt=getKey(datTree,'pt')[datHiggsId == 0][:,0], 
    eta=getKey(datTree,'eta')[datHiggsId == 0][:,0], 
    phi=getKey(datTree,'phi')[datHiggsId == 0][:,0], 
    m=getKey(datTree,'m')[datHiggsId == 0][:,0])
H1_b2 = vector.obj(
    pt=getKey(datTree,'pt')[datHiggsId == 0][:,1], 
    eta=getKey(datTree,'eta')[datHiggsId == 0][:,1], 
    phi=getKey(datTree,'phi')[datHiggsId == 0][:,1], 
    m=getKey(datTree,'m')[datHiggsId == 0][:,1])
H2_b1 = vector.obj(
    pt=getKey(datTree,'pt')[datHiggsId == 1][:,0], 
    eta=getKey(datTree,'eta')[datHiggsId == 1][:,0], 
    phi=getKey(datTree,'phi')[datHiggsId == 1][:,0], 
    m=getKey(datTree,'m')[datHiggsId == 1][:,0])
H2_b2 = vector.obj(
    pt=getKey(datTree,'pt')[datHiggsId == 1][:,1], 
    eta=getKey(datTree,'eta')[datHiggsId == 1][:,1], 
    phi=getKey(datTree,'phi')[datHiggsId == 1][:,1], 
    m=getKey(datTree,'m')[datHiggsId == 1][:,1])
H3_b1 = vector.obj(
    pt=getKey(datTree,'pt')[datHiggsId == 2][:,0], 
    eta=getKey(datTree,'eta')[datHiggsId == 2][:,0], 
    phi=getKey(datTree,'phi')[datHiggsId == 2][:,0], 
    m=getKey(datTree,'m')[datHiggsId == 2][:,0])
H3_b2 = vector.obj(
    pt=getKey(datTree,'pt')[datHiggsId == 2][:,1], 
    eta=getKey(datTree,'eta')[datHiggsId == 2][:,1], 
    phi=getKey(datTree,'phi')[datHiggsId == 2][:,1], 
    m=getKey(datTree,'m')[datHiggsId == 2][:,1])

X = H1_b1 + H1_b2 + H2_b1 + H2_b2 + H3_b1 + H3_b2

print("Building masks...")

dat_6jNN_mask = datTree.b_6j_score > cut_6jNN # pass 6jNN mask
# dat_pT30_mask = ak.all(datTree.t6_jet_pt > 30, axis=1) & dat_6jNN_mask # all t6 jets have pT > 30 GeV

# dat_m_cand = datTree.t6_higgs_m[:,2]
dat_Dm_cand = abs(datTree.t6_higgs_m - 125)

# mass veto
dat_SR = (dat_6jNN_mask) & ak.all(dat_Dm_cand <= SR_edge, axis=1) # SR
dat_VR = (dat_6jNN_mask) & ak.all(dat_Dm_cand > SR_edge, axis=1) & ak.all(dat_Dm_cand <= VR_edge, axis=1) # VR
dat_CR = (dat_6jNN_mask) & ak.all(dat_Dm_cand > VR_edge, axis=1) # CR

# data_sums = ak.sum(datTree.t6_jet_btag, axis=1)[dat_CR]/6
# n_data, edges = np.histogram(data_sums.to_numpy(), bins=score_bins)

print("Diving regions...")

# score veto
dat_ls_mask = ak.sum(datTree.t6_jet_btag, axis=1)/6 < btag_sum_cut # ls
dat_hs_mask = ak.sum(datTree.t6_jet_btag, axis=1)/6 >= btag_sum_cut # hs

# combination
dat_CRls_mask = dat_6jNN_mask & dat_CR & dat_ls_mask
dat_CRhs_mask = dat_6jNN_mask & dat_CR & dat_hs_mask
dat_VRls_mask = dat_6jNN_mask & dat_VR & dat_ls_mask
dat_VRhs_mask = dat_6jNN_mask & dat_VR & dat_hs_mask
dat_SRls_mask = dat_6jNN_mask & dat_SR & dat_ls_mask

print("Calculating transfer factor...")
TF = ak.sum(dat_CRhs_mask)/ak.sum(dat_CRls_mask)

max_mass = 2000
nbins = 100
n_dat_SRls, e = np.histogram(X.m[dat_SRls_mask].to_numpy(), bins=np.linspace(0,max_mass,nbins))
x = x_bins(e)
ax, n_dat_SRls_transformed, e = Hist(x, weights=n_dat_SRls*TF, bins=np.linspace(0,max_mass,nbins), label='bkg model')

B = int(n_dat_SRls_transformed.sum())

nEvents.append([
    'Data',
    ak.sum(dat_SR),
    ak.sum(dat_VR),
    ak.sum(dat_CR)
    ])

nBreakdown.append([
    'Data',
    B,
    ak.sum(dat_SRls_mask),
    ak.sum(dat_VRhs_mask),
    ak.sum(dat_VRls_mask),
    ak.sum(dat_CRhs_mask),
    ak.sum(dat_CRls_mask),
    ])

print("Building ROOT canvas...")

fout = ROOT.TFile(f"mass_info/sig_dat_mX.root","recreate")
fout.cd()

canvas = ROOT.TCanvas()
h_dat = ROOT.TH1D("h_dat",";m_{X} [GeV];Counts",len(n_dat_SRls_transformed),array('d',list(e)))
for i,bin_dat in enumerate(n_dat_SRls_transformed):
    h_dat.SetBinContent(i+1, bin_dat)
h_dat.Draw()
h_dat.Write()

Print("Processing signal...")
for MASS_PAIR in NMSSM_List:
# for MASS_PAIR in [NMSSM_List[0],NMSSM_List[2],NMSSM_List[5]]:
    mxmy = MASS_PAIR.split('/')[-2]
    Print(mxmy)
    sigTree = Signal(MASS_PAIR)
    sigHiggsId = sigTree.t6_jet_higgsIdx

    print("Building mX...")

    sig_H1_b1 = vector.obj(
        pt=getKey(sigTree,'pt')[sigHiggsId == 0][:,0], 
        eta=getKey(sigTree,'eta')[sigHiggsId == 0][:,0], 
        phi=getKey(sigTree,'phi')[sigHiggsId == 0][:,0], 
        m=getKey(sigTree,'m')[sigHiggsId == 0][:,0])
    sig_H1_b2 = vector.obj(
        pt=getKey(sigTree,'pt')[sigHiggsId == 0][:,1], 
        eta=getKey(sigTree,'eta')[sigHiggsId == 0][:,1], 
        phi=getKey(sigTree,'phi')[sigHiggsId == 0][:,1], 
        m=getKey(sigTree,'m')[sigHiggsId == 0][:,1])
    sig_H2_b1 = vector.obj(
        pt=getKey(sigTree,'pt')[sigHiggsId == 1][:,0], 
        eta=getKey(sigTree,'eta')[sigHiggsId == 1][:,0], 
        phi=getKey(sigTree,'phi')[sigHiggsId == 1][:,0], 
        m=getKey(sigTree,'m')[sigHiggsId == 1][:,0])
    sig_H2_b2 = vector.obj(
        pt=getKey(sigTree,'pt')[sigHiggsId == 1][:,1], 
        eta=getKey(sigTree,'eta')[sigHiggsId == 1][:,1], 
        phi=getKey(sigTree,'phi')[sigHiggsId == 1][:,1], 
        m=getKey(sigTree,'m')[sigHiggsId == 1][:,1])
    sig_H3_b1 = vector.obj(
        pt=getKey(sigTree,'pt')[sigHiggsId == 2][:,0], 
        eta=getKey(sigTree,'eta')[sigHiggsId == 2][:,0], 
        phi=getKey(sigTree,'phi')[sigHiggsId == 2][:,0], 
        m=getKey(sigTree,'m')[sigHiggsId == 2][:,0])
    sig_H3_b2 = vector.obj(
        pt=getKey(sigTree,'pt')[sigHiggsId == 2][:,1], 
        eta=getKey(sigTree,'eta')[sigHiggsId == 2][:,1], 
        phi=getKey(sigTree,'phi')[sigHiggsId == 2][:,1], 
        m=getKey(sigTree,'m')[sigHiggsId == 2][:,1])

    sig_X = sig_H1_b1 + sig_H1_b2 + sig_H2_b1 + sig_H2_b2 + sig_H3_b1 + sig_H3_b2

    print("Building masks...")

    sig_6jNN_mask = sigTree.b_6j_score > cut_6jNN # pass 6jNN mask
    # sig_pT30_mask = ak.all(sigTree.t6_jet_pt > 30, axis=1) & sig_6jNN_mask # all t6 jets have pT > 30 GeV

    sig_Dm_cand = abs(sigTree.t6_higgs_m - 125)

    # mass veto
    sig_SR = (sig_6jNN_mask) & ak.all(sig_Dm_cand <= SR_edge, axis=1) # SR
    sig_VR = (sig_6jNN_mask) & ak.all(sig_Dm_cand > SR_edge, axis=1) & ak.all(sig_Dm_cand <= VR_edge, axis=1) # SR
    sig_CR = (sig_6jNN_mask) & ak.all(sig_Dm_cand > VR_edge, axis=1) # CR

    nEvents.append([
        sigTree.mXmY,
        ak.sum(sig_SR),
        ak.sum(sig_VR),
        ak.sum(sig_CR)
        ])

    sig_sums = ak.sum(sigTree.t6_jet_btag, axis=1)[sig_SR]/6
    n_sig, edges = np.histogram(sig_sums.to_numpy(), bins=score_bins)

    # sum6_eff = []
    # sum6_rej = []

    # for cut in edges[:-1]:
    #     sum6_eff.append(n_sig[edges[:-1] >= cut].sum()/n_sig.sum())
    #     sum6_rej.append(n_data[edges[:-1] < cut].sum()/n_data.sum())

    # sum6_eff = np.append(1, np.asarray(sum6_eff))
    # sum6_rej = np.asarray(sum6_rej)

    # dx = sum6_eff[:-1] - sum6_eff[1:]
    # auc = np.sum(sum6_rej*dx)
    # sum6_rej = np.append(sum6_rej, 1)

    # opt_arg = (abs(sum6_eff-auc)+abs(sum6_rej-auc)).argmin()

    # # opt_cut = True
    # opt_cut = False
    # if opt_cut:
    #     opt_cut = score_bins[opt_arg]
    #     Print(Fore.GREEN + f"Optimal score cut = {opt_cut}")
    # else:
    #     opt_cut = 0.68
    #     Print(Fore.GREEN + f"PRESET score cut = {opt_cut}")

    print("Dividing regions...")

    # score veto
    sig_ls_mask = ak.sum(sigTree.t6_jet_btag, axis=1)/6 < btag_sum_cut # ls
    sig_hs_mask = ak.sum(sigTree.t6_jet_btag, axis=1)/6 >= btag_sum_cut # hs

    # combination
    sig_SRhs_mask = sig_SR & sig_hs_mask
    sig_SRls_mask = sig_SR & sig_ls_mask
    sig_VRhs_mask = sig_VR & sig_hs_mask
    sig_VRls_mask = sig_VR & sig_ls_mask
    sig_CRhs_mask = sig_CR & sig_hs_mask
    sig_CRls_mask = sig_CR & sig_ls_mask

    # mX = int(sigTree.sample.split(' ')[1])
    # mY = int(sigTree.sample.split(' ')[4])

    # xmin = mX - 0.3*mX
    # xmax = mX + 0.15*mX

    n_sig_SRhs, e = Hist(sig_X.m[sig_SRhs_mask], bins=np.linspace(0,max_mass,nbins), label='SR-hs', scale=sigTree.scale, ax=ax)

    n_sig_SRls, e = np.histogram(sig_X.m[sig_SRls_mask].to_numpy(), bins=np.linspace(0,max_mass,nbins))
    n_sig_VRhs, e = np.histogram(sig_X.m[sig_VRhs_mask].to_numpy(), bins=np.linspace(0,max_mass,nbins))
    n_sig_VRls, e = np.histogram(sig_X.m[sig_VRls_mask].to_numpy(), bins=np.linspace(0,max_mass,nbins))
    n_sig_CRhs, e = np.histogram(sig_X.m[sig_CRhs_mask].to_numpy(), bins=np.linspace(0,max_mass,nbins))
    n_sig_CRls, e = np.histogram(sig_X.m[sig_CRls_mask].to_numpy(), bins=np.linspace(0,max_mass,nbins))

    S = int(n_sig_SRhs.sum())

    nBreakdown.append([
        sigTree.mXmY,
        S,
        int(n_sig_SRls.sum()*sigTree.scale),
        int(n_sig_VRhs.sum()*sigTree.scale),
        int(n_sig_VRls.sum()*sigTree.scale),
        int(n_sig_CRhs.sum()*sigTree.scale),
        int(n_sig_CRls.sum()*sigTree.scale),
        ])


    print("Building ROOT histograms...")

    h_sig = ROOT.TH1D(f"h_sig_{sigTree.mXmY}",";m_{X} [GeV];Counts",len(n_sig_SRhs),array('d',list(e)))

    for i,bin_sig in enumerate(n_sig_SRhs):
        h_sig.SetBinContent(i+1, bin_sig)

    h_sig.Draw("same")
    h_sig.Write()
    canvas.Draw()

table = AsciiTable(nEvents)
print(table.table)

table = AsciiTable(nBreakdown)
print(table.table)

fout.Close()

    # sigma = int(np.sqrt(B))
    # mu = 2*np.sqrt(B)/S
    # sensitivity = sigTree.xsec*mu

    # print(sigTree.mXmY)
    # print(f"    Number of signal events = {S}")
    # print(f"Number of background events = {B}")
    # print(f"    Standard Deviation of B = {sigma}")
    # print(f"                         mu = {mu:.3f}")
    # print(Fore.LIGHTMAGENTA_EX + f"                      limit = {int(sensitivity*1000)} fb")
    # print()

    # dcText = buildDataCard(S,B,.1)

    # dcName = f'datacard_{sigTree.mXmY}_sys.txt'
    # with open(DataCards_dir + dcName,"w") as f:
    #     f.writelines(dcText)
    # print("Created file")
    # print(dcName)