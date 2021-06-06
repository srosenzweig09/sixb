"""
This will be a class that collects the six bs from the signal event and returns their p4s.
"""

from particle import Particle
import awkward as ak
import itertools
import numpy as np
import random
import vector

from colors import CYAN, W
from logger import info
from myuproot import open_up
from tqdm import tqdm

def get_6jet_p4(filename=None):

    vector.register_awkward()
    signal_builder = ak.ArrayBuilder()
    bkgd_builder = ak.ArrayBuilder()
    
    if filename:
        reco_filename = filename
    else:
        reco_filename = f'signal/NanoAOD/NMSSM_XYH_YToHH_6b_MX_700_MY_400_reco_preselections.root'
        # reco_filename = 'signal/NanoAOD/NMSSM_XYH_YToHH_6b_MX_700_MY_400_accstudies_500k_May2021.root'
        
    info(f"Opening ROOT file {CYAN}{reco_filename}{W} with columns")
    tree, table, nptab =  open_up(reco_filename, 'sixBtree')
    nevents = len(table)
    
    jet_idx = nptab['jet_idx']
    jet_pt = nptab['jet_pt']
    jet_eta = nptab['jet_eta']
    jet_phi = nptab['jet_phi']
    jet_m = nptab['jet_m']
    jet_btag = nptab['jet_btag']
    signal_idx = []
    signal_btag = []
    background_btag = []
    
    # signal_p4 = []
    # background_p4 = []
    global_list = [] # list of events

    # b_mass = Particle.from_pdgid(5).mass / 1000 # Convert from MeV to GeV
    available_bkgd = []

    pass_count = 0
    for evt in tqdm(range(nevents)):

        # Make a mask for jets matched to signal bs
        signal_mask = np.array(([i for i,obj in enumerate(jet_idx[evt]) if obj > -1]))
        
        # Mask the background jets
        background_mask = [i for i,obj in enumerate(jet_idx[evt]) if obj == -1]
        # Cound the background jets
        n_nonHiggs = len(jet_pt[evt][background_mask])
        
        # Skip and events with less than 6 matching signal bs (for now)
        if len(jet_pt[evt][signal_mask]) < 6: continue
        # Skip any events with duplicate matches (for now)
        if len(np.unique(jet_idx[evt][signal_mask])) < len(jet_idx[evt][signal_mask]): continue
        if (n_nonHiggs < 1): continue
        available_bkgd.append(n_nonHiggs)

        evt_list = [] # list of dictionaries

        # n_bkgd = np.min(n_nonHiggs, 6)
        # n_sig = 6 - n_bkgd
        # random_nonHiggs = random.choices(np.arange(1,n_nonHiggs), k=n_bkgd)
        # random_signalb_to_replace = random.choices(np.arange(0,6), k=n_bkgd)

        if n_nonHiggs > 1:
            # Choose a random background jet
            # n_bkgd = random.randint(1,n_nonHiggs)
            n_bkgd = n_nonHiggs
            random_nonHiggs = random.choices(np.arange(1,n_nonHiggs), k=n_bkgd)
            random_signalb_to_replace = random.choices(np.arange(0,6), k=n_bkgd)
        else:
            random_nonHiggs = [0]
            random_signalb_to_replace = random.choices(np.arange(0,6), k=1)
        
        sixb_pt = jet_pt[evt][signal_mask]
        non_sixb_pt = sixb_pt.copy()
        for nH, sb in zip(random_nonHiggs, random_signalb_to_replace):
            bkgd_pt = jet_pt[evt][background_mask][nH]
            non_sixb_pt[sb] = bkgd_pt
        
        sixb_eta = jet_eta[evt][signal_mask]
        non_sixb_eta = sixb_eta.copy()
        for nH, sb in zip(random_nonHiggs, random_signalb_to_replace):
            bkgd_eta = jet_eta[evt][background_mask][nH]
            non_sixb_eta[sb] = bkgd_eta
        
        sixb_phi = jet_phi[evt][signal_mask]
        non_sixb_phi = sixb_phi.copy()
        for nH, sb in zip(random_nonHiggs, random_signalb_to_replace):
            bkgd_phi = jet_phi[evt][background_mask][nH]
            non_sixb_phi[sb] = bkgd_phi

        sixb_m = jet_m[evt][signal_mask]
        non_sixb_m = sixb_m.copy()
        for nH, sb in zip(random_nonHiggs, random_signalb_to_replace):
            bkgd_m = jet_m[evt][background_mask][nH]
            non_sixb_m[sb] = bkgd_m

        sixb_btag = jet_btag[evt][signal_mask]
        non_sixb_btag = sixb_btag.copy()
        for nH, sb in zip(random_nonHiggs, random_signalb_to_replace):
            bkgd_btag = jet_btag[evt][background_mask][nH]
            non_sixb_btag[sb] = bkgd_btag

        sixb_idx = signal_mask[np.argsort(sixb_pt)][::-1]
        signal_idx.append(sixb_idx)
        
        sixb_eta  = sixb_eta[np.argsort(sixb_pt)][::-1]
        sixb_phi  = sixb_phi[np.argsort(sixb_pt)][::-1]
        sixb_m    = sixb_m[np.argsort(sixb_pt)][::-1]
        sixb_btag = sixb_btag[np.argsort(sixb_pt)][::-1]
        signal_btag.append(sixb_btag)
        sixb_pt   = np.sort(sixb_pt)[::-1]
        
        non_sixb_eta  = non_sixb_eta[np.argsort(non_sixb_pt)][::-1]
        non_sixb_phi  = non_sixb_phi[np.argsort(non_sixb_pt)][::-1]
        non_sixb_m    = non_sixb_m[np.argsort(non_sixb_pt)][::-1]
        non_sixb_btag = non_sixb_btag[np.argsort(non_sixb_pt)][::-1]
        background_btag.append(non_sixb_btag)
        non_sixb_pt   = np.sort(non_sixb_pt)[::-1]


        with signal_builder.list():

            for pt, eta, phi, m in zip(sixb_pt, sixb_eta, sixb_phi, sixb_m):

                with signal_builder.record("Momentum4D"):   # not MomentumObject4D

                    signal_builder.field("pt"); signal_builder.real(pt)

                    signal_builder.field("eta"); signal_builder.real(eta)

                    signal_builder.field("phi"); signal_builder.real(phi)

                    signal_builder.field("m"); signal_builder.real(m)

        with bkgd_builder.list():

                for pt, eta, phi,m  in zip(non_sixb_pt, non_sixb_eta, non_sixb_phi, non_sixb_m):

                    with bkgd_builder.record("Momentum4D"):   # not MomentumObject4D

                        bkgd_builder.field("pt"); bkgd_builder.real(pt)

                        bkgd_builder.field("eta"); bkgd_builder.real(eta)

                        bkgd_builder.field("phi"); bkgd_builder.real(phi)

                        bkgd_builder.field("m"); bkgd_builder.real(m)

    signal_p4 = signal_builder.snapshot()
    bkgd_p4 = bkgd_builder.snapshot()
    signal_idx = np.array((signal_idx))
    signal_btag = np.array((signal_btag))
    bkgd_btag = np.array((bkgd_btag))
        
    return signal_p4, bkgd_p4, signal_idx, signal_btag, background_btag, available_bkgd







def get_sixb_p4(filename=None):
    
    if filename:
        reco_filename = filename
    else:
        reco_filename = f'signal/NanoAOD/NMSSM_XYH_YToHH_6b_MX_700_MY_400_reco_preselections.root'
        
    info(f"Opening ROOT file {CYAN}{reco_filename}{W} with columns")
    tree, table, nptab =  open_up(reco_filename, 'sixBtree')
    nevents = len(table)

    HX_b1  = {'pt': nptab[f'HX_b1_recojet_ptRegressed' ],
            'eta':nptab[f'HX_b1_recojet_eta'],
            'phi':nptab[f'HX_b1_recojet_phi'],
            'm':  nptab[f'HX_b1_recojet_m'  ]}
    HX_b2  = {'pt': nptab[f'HX_b2_recojet_ptRegressed' ],
            'eta':nptab[f'HX_b2_recojet_eta'],
            'phi':nptab[f'HX_b2_recojet_phi'],
            'm':  nptab[f'HX_b2_recojet_m'  ]}
    HY1_b1 = {'pt': nptab[f'HY1_b1_recojet_ptRegressed'],
            'eta':nptab[f'HY1_b1_recojet_eta'],
            'phi':nptab[f'HY1_b1_recojet_phi'],
            'm':  nptab[f'HY1_b1_recojet_m' ]}
    HY1_b2 = {'pt': nptab[f'HY1_b2_recojet_ptRegressed'],
            'eta':nptab[f'HY1_b2_recojet_eta'],
            'phi':nptab[f'HY1_b2_recojet_phi'],
            'm':  nptab[f'HY1_b2_recojet_m' ]}
    HY2_b1 = {'pt': nptab[f'HY2_b1_recojet_ptRegressed'],
            'eta':nptab[f'HY2_b1_recojet_eta'],
            'phi':nptab[f'HY2_b1_recojet_phi'],
            'm':  nptab[f'HY2_b1_recojet_m' ]}
    HY2_b2 = {'pt': nptab[f'HY2_b2_recojet_ptRegressed'],
            'eta':nptab[f'HY2_b2_recojet_eta'],
            'phi':nptab[f'HY2_b2_recojet_phi'],
            'm':  nptab[f'HY2_b2_recojet_m' ]}

    part_dict = {0:HX_b1, 1:HX_b2, 2:HY1_b1, 3:HY1_b2, 4:HY2_b1, 5:HY2_b2}
    part_name = {0:'HX_b1', 1:'HX_b2', 2:'HY1_b1', 3:'HY1_b2', 4:'HY2_b1', 5:'HY2_b2'}
    pair_dict = {0:1, 1:0, 2:3, 3:2, 4:5, 5:4} # Used later to verify that non-Higgs
                                            # pair candidates are truly non-Higgs pairs

    nonHiggs_labels = np.array((
    'X b1, Y1 b1',
    'X b1, Y1 b2',
    'X b1, Y2 b1',
    'X b1, Y2 b2',
    'X b2, Y1 b1',
    'X b2, Y1 b2',
    'X b2, Y2 b1',
    'X b2, Y2 b2',
    'Y1 b1, Y2 b1',
    'Y1 b1, Y2 b2',
    'Y1 b2, Y2 b1',
    'Y1 b2, Y2 b2'))

    signal_b_p4 = []
    for i in range(6):
        signal_b_p4.append(vector.obj(
            pt=part_dict[i]['pt'], 
            eta=part_dict[i]['eta'], 
            phi=part_dict[i]['phi'], 
            mass=np.repeat(4, nevents)))
        
    return signal_b_p4

def get_background_p4(filename=None):
    
    if filename:
        reco_filename = filename
    else:
        reco_filename = f'signal/NanoAOD/NMSSM_XYH_YToHH_6b_MX_700_MY_400_reco_preselections.root'
        # reco_filename = 'signal/NanoAOD/NMSSM_XYH_YToHH_6b_MX_700_MY_400_accstudies_500k_May2021.root'
        
    info(f"Opening ROOT file {CYAN}{reco_filename}{W} with columns")
    tree, table, nptab =  open_up(reco_filename, 'sixBtree')
    nevents = len(table)
    
    jet_idx = nptab['jet_idx']
    jet_pt = nptab['jet_pt']
    jet_eta = nptab['jet_eta']
    jet_phi = nptab['jet_phi']
#     jet_m = nptab['jet_m']
#     jet_btag = nptab['jet_btag']
    
    signal_p4 = []
    background_p4 = []
    
    pass_count = 0
    for evt in tqdm(range(nevents)):
        # Make a mask for jets matched to signal bs
        signal_mask = [i for i,obj in enumerate(jet_idx[evt]) if obj > -1]
        # if len(jet_pt[evt][signal_mask]) < 6: continue
        # Skip any events with duplicate matches (for now)
        # if len(np.unique(jet_idx[evt][signal_mask])) < len(jet_idx[evt][signal_mask]): continue
        # Skip and events with less than 6 matching signal bs (for now)
        
        # Mask the background jets
        background_mask = [i for i,obj in enumerate(jet_idx[evt]) if obj == -1]
        # Cound the background jets
        n_nonHiggs = len(jet_pt[evt][background_mask])
        if (n_nonHiggs < 6): continue
        pass_count += 1
        
        bkgd_pt = jet_pt[evt][background_mask][:6]
        bkgd_eta = jet_eta[evt][background_mask][:6]
        bkgd_phi = jet_phi[evt][background_mask][:6]
        # Choose a random background jet
        
        bkgd_pt = np.sort(bkgd_pt)
        bkgd_eta = bkgd_eta[np.argsort(bkgd_pt)]
        bkgd_phi = bkgd_phi[np.argsort(bkgd_pt)]

        background_p4.append(vector.obj(
                        pt=bkgd_pt, 
                        eta=bkgd_eta, 
                        phi=bkgd_phi, 
                        mass=np.repeat(4, 6)))
        
    print(pass_count)
        
    return background_p4