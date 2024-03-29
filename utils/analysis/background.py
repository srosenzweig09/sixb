""" 
Author: Suzanne Rosenzweig
"""

from utils import *
from utils.varUtils import *
from utils.cutConfig import *
from utils.plotter import Hist
from utils.analysis.particle import Particle
from utils.analysis.feyn import Model

# Standard library imports
from configparser import ConfigParser

import subprocess, shlex
import sys 
import uproot

vector.register_awkward()

years = ['2016', '2017', '2018']

def get_scaled_weights(list_of_arrs, bins, scale):
    """This function is used to get weights for background events."""
    n = np.zeros_like(bins[:-1])
    for i,(sample, scale) in enumerate(zip(list_of_arrs, scale)):
        try: branch = sample.to_numpy()
        except: branch = ak.flatten(sample).to_numpy()
        n_i, b = np.histogram(branch, bins)
        centers = (b[1:] + b[:-1])/2
        # print(n_i)
        # print(scale)
        try: n += n_i*scale
        except: n += n_i
    return n, b, centers

def get_region_mask(higgs, center, sr_edge, cr_edge):
        deltaM = np.column_stack(([abs(mH.to_numpy() - val) for mH,val in zip(higgs,center)]))
        deltaM = deltaM * deltaM
        deltaM = deltaM.sum(axis=1)
        deltaM = np.sqrt(deltaM)

        sr_mask = deltaM <= sr_edge 
        cr_mask = (deltaM > sr_edge) & (deltaM <= cr_edge) 

        return sr_mask, cr_mask

def get_hs_ls_masks(sr_mask, cr_mask, ls_mask, hs_mask):
   cr_ls_mask = cr_mask & ls_mask
   cr_hs_mask = cr_mask & hs_mask
   sr_ls_mask = sr_mask & ls_mask
   sr_hs_mask = sr_mask & hs_mask

   return cr_ls_mask, cr_hs_mask, sr_ls_mask, sr_hs_mask

class Bkg():
    
    def __init__(self, filename, treename='sixBtree', year=2018, feyn=True, floc=None):
        """
        A class for handling TTrees from older skims, which output an array of jet kinematics. (Newer skims output a single branch for each b jet kinematic.)

        args:
            filename: string containing name of a single file OR a list of several files to open
            treename: default is 'sixBtree,' which is the named TTree output from the analysis code

        returns:
            Nothing. Initializes attributes of Tree class.
        """

        self.year = year

        if type(filename) != list:
            self.single_init(filename, treename, year, feyn=feyn, floc=floc)
        else:
            self.multi_init(filename, treename, year, feyn=feyn, floc=floc)

    def single_init(self, filename, treename, year, feyn, floc):
        """Opens a single file into a TTree"""
        self.single = True
        tree = uproot.open(f"{filename}:{treename}")
        self.tree = tree

        # if not exploration:
        #     for k, v in tree.items():
        #         if ('t6' in k) or ('score' in k) or ('nn' in k): 
        #             setattr(self, k, v.array())
        #             used_key = k
        # else:            
        for k, v in tree.items():
            if (k.startswith('jet_') or (k.startswith('H_'))):
                setattr(self, k, v.array())
                used_key = k

        self.nevents = len(tree[used_key].array())


        cutflow = uproot.open(f"{filename}:h_cutflow")
        # save total number of events for scaling purposes
        total = cutflow.to_numpy()[0][0]
        _, xsec = next( ((key,value) for key,value in xsecMap.items() if key in filename),("unk",1) )
        # if signal: 
        #     self.sample = latexTitle(filename)
        #     self.mXmY = self.sample.replace('$','').replace('_','').replace('= ','_').replace(', ','_').replace(' GeV','')
        self.xsec = xsec
        self.lumi = lumiMap[year][0]
        self.scale = self.lumi*xsec/total
        self.cutflow = cutflow.to_numpy()[0]*self.scale
        self.cutflow_labels = cutflow.axis().labels()

        # self.genWeight = self.lumi*xsec*tree['genWeight'].array()
        self.PUWeight = tree['PUWeight'].array()
        self.PUWeight_up = tree['PUWeight_up'].array()
        self.PUWeight_down = tree['PUWeight_down'].array()
        # self.PUIDWeight = tree['PUIDWeight'].array()
        # self.PUIDWeight_up = tree['PUIDWeight_up'].array()
        # self.PUIDWeight_down = tree['PUIDWeight_down'].array()
        # self.triggerSF = tree['triggerScaleFactor'].array()
        # self.triggerSF_up = tree['triggerScaleFactorUp'].array()
        # self.triggerSF_down = tree['triggerScaleFactorDown'].array()

        samp, xsec = next( ((key,value) for key,value in xsecMap.items() if key in filename),("unk",1) )
        if feyn:
            # samp_file = 
            with uproot.open(samp_file) as f:
                f = f['Events']
                self.scores = f['scores'].array(library='np')
                self.maxcomb = f['max_comb'].array(library='np')
                self.maxscore = f['max_score'].array()
                self.maxlabel = f['max_label'].array()
                self.minscore = f['min_score'].array()
                self.nres_rank = f['nres_rank'].array()
                self.mass_rank = f['mass_rank'].array()
                self.max_diff = np.sort(self.scores, axis=1)[:,44]-np.sort(self.scores, axis=1)[:,43]
            self.init_from_gnn()



    def multi_init(self, filelist, treename, year, feyn, floc=None):
        """Opens a list of files into several TTrees. Typically used for bkgd events."""
        self.single = False
        self.is_signal = False
        self.is_bkgd = True

        arr_trees = []
        arr_xsecs = []
        arr_nevent = []
        arr_sample = []
        arr_total = []
        self.arr_n = []
        self.maxcomb = []
        self.scores = []
        self.maxscores = []
        self.minscores = []
        self.nres_rank = []
        self.mass_rank = []

        self.cutflow = np.zeros(11)
        self.cutflows = []

        qcd_mask = np.array(())

        print('/'.join(filelist[0].split('/')[:8]))
        for filename in filelist:
            file_info = '/'.join(filename.split('/')[8:])
            fname = filename.split('/')[-2]
            print(file_info)
            # Open tree
            try: uproot.open(f"{filename}:{treename}")
            except FileNotFoundError: 
                print(f"[FILE NOT FOUND] .. skipping {file_info}")
                continue
            except uproot.KeyInFileError:
                print(f"[NO KEYS IN FILE] .. skipping {file_info}")
                continue
            except:
                print(f"[ERROR] {file_info}")
                continue

            # with uproot.open(f"{filename}:{treename}") as tree:
            if 'QCD' in filename: stepsize=100000
            else: stepsize=2200000
            for tree in uproot.iterate(f"{filename}:{treename}", step_size=stepsize):
                # How many events in the tree?

                # CHANGED FOR UPROOT ITERATE
                # n = len(tree['jet_pt'].array())
                n = len(tree['jet_pt'])
                
                if n == 0: 
                    print(f".. skipping {file_info}")
                    continue

                if 'QCD' in filename: qcd_mask = np.append(qcd_mask, np.repeat(1,n))
                else: qcd_mask = np.append(qcd_mask, np.repeat(0,n))
                
                self.arr_n.append(n)
                cutflow = uproot.open(f"{filename}:h_cutflow")
                self.cutflow_labels = cutflow.axis().labels()
                # save total number of events for scaling purposes
                samp_tot = cutflow.to_numpy()[0][0]
                cf = cutflow.to_numpy()[0]
                if len(cf) < 11: cf = np.append(cf, np.zeros(11-len(cf)))
                if n == 0: continue # Skip if no events
                arr_total.append(samp_tot)
                arr_nevent.append(n)
                # Bkgd events must be scaled to the appropriate xs in order to compare fairly with signal yield
                samp, xsec = next( ((key,value) for key,value in xsecMap.items() if key in filename),("unk",1) )
                # print(samp)
                # print(samp_file)
                if feyn:
                    if floc is None: feyn_file = f"{model_path}/{self.year}/{fname}.root"
                    else: feyn_file = f"{floc}/{fname}.root"
                    # samp_file = f"{model_path}/{[i for i in predictions if samp in i][0]}"
                    with uproot.open(feyn_file) as f:
                        f = f['Events']
                        self.scores = f['scores'].array(library='np')
                        self.maxcomb.append(f['max_comb'].array(library='np'))
                        self.maxscore = f['max_score'].array()
                        self.maxlabel = f['max_label'].array()
                        self.minscore = f['min_score'].array()
                        self.nres_rank = f['nres_rank'].array()
                        self.mass_rank = f['mass_rank'].array()
                        self.max_diff = np.sort(self.scores, axis=1)[:,44]-np.sort(self.scores, axis=1)[:,43]
                        
                    # self.maxlabel = f_awk['maxlabel']

                self.cutflow += cf[:11] * lumiMap[year][0] * xsec / samp_tot
                self.cutflows.append(cf[cf > 0])
                arr_trees.append(tree)
                arr_xsecs.append(xsec)
                arr_sample.append(samp)
                setattr(self, samp, tree)

                # CHANGED FOR UPROOT ITERATE
                # for k in ak.fields(tree):
                #     print(getattr(self, samp))
                #     setattr(getattr(self, samp), k, tree[k])

        
        self.qcd_mask = qcd_mask == 1
        self.ttbar_mask = ~self.qcd_mask
        self.ntrees = len(arr_trees)
        self.tree = arr_trees
        self.xsec = arr_xsecs
        self.lumi = lumiMap[year][0]
        self.nevents = arr_nevent
        print(self.nevents)
        self.sample = arr_sample
        self.total = arr_total
        self.scales = self.lumi*np.asarray(arr_xsecs)/np.asarray(arr_total)
        self.scale = np.repeat(self.scales, np.array(self.arr_n))
        # self.weighted_n = np.asarray(self.nevents)*self.scale


        # for k in tree.keys():
        for k in ak.fields(tree):
            if 'jet' in k or k.startswith('H') or k.startswith('Y') or k.startswith('X'):
                leaves = []
                for samp in self.sample:
                    try:
                        arr = getattr(getattr(self, samp), k)
                        leaves.append(arr)
                    except: pass
                setattr(self, k, leaves)

        self.year = int([yr for yr in years if yr in filename][0])

        if feyn: self.init_from_gnn()
        else: self.init_from_cuts()

    def hist(self, var, bins, mask=None, ax=None, plot_mode='together', colors=['green', 'rebeccapurple'], labels=['ttbar', 'qcd'], all_jets=False, **kwargs):
        """
        plot_mode = {
            'together' : qcd and ttbar will be plotted as one curve,
            'stacked' : qcd and ttbar will be plotted stacked,
            'separate' : qcd and ttbar will be plotted separately
        }
        """
        if ax == None: fig, ax = plt.subplots()
        if isinstance(var, list):
            if isinstance(var[0], np.ndarray): 
                try: var = np.concatenate(var)
                except: pass
            elif isinstance(var[0], ak.Array): 
                print("Concatenating awkward arrays...")
                try: var = ak.concatenate(var)
                except: pass
        
        if 'color' not in kwargs.keys(): kwargs['color'] = 'black'

        if mask is not None:
            ttbar_mask = self.ttbar_mask & mask
            qcd_mask = self.qcd_mask & mask
        else:
            ttbar_mask = self.ttbar_mask
            qcd_mask = self.qcd_mask

        if plot_mode == 'separate':
            if 'label' in kwargs.keys(): kwargs.pop('label')
            kwargs['color'] = colors[0]
            n_ttbar = Hist(var[ttbar_mask], bins=bins, weights=self.scale[ttbar_mask], ax=ax, label=labels[0], **kwargs)
            kwargs['color'] = colors[1]
            n_qcd = Hist(var[qcd_mask], bins=bins, weights=self.scale[qcd_mask], ax=ax, label=labels[1], **kwargs)
            ax.legend()
            return n_qcd, n_ttbar
        elif plot_mode == 'stacked':
            kwargs['color'] = colors[0]
            n_ttbar = Hist(var[ttbar_mask], bins=bins, weights=self.scale[ttbar_mask], ax=ax, label=labels[0], **kwargs)
            kwargs['color'] = colors[1]
            n_qcd = Hist(var[qcd_mask], bins=bins, weights=self.scale[qcd_mask], ax=ax, label=labels[1], bottom=n_ttbar, **kwargs)
            ax.legend()
            return n_qcd, n_ttbar
        
        scale = self.scale
        if mask is not None: 
            var = var[mask]
            scale = self.scale[mask]

        return Hist(var, bins=bins, weights=scale, ax=ax, **kwargs)

    def keys(self):
        print(self.tree.keys())

    def get(self, key):
        return [tree[key] for tree in self.tree]
        # return [tree[key].array() for tree in self.tree]

    def init_from_gnn(self):
        if self.single:
            combos = self.maxcomb.astype(int)
            combos = ak.from_regular(combos)
            self.combos = combos

            pt = self.jet_ptRegressed[combos]
            eta = self.jet_eta[combos]
            phi = self.jet_phi[combos]
            m = self.jet_mRegressed[combos]
            btag = self.jet_btag[combos]
        else:
            combos = [maxcomb.astype(int) for maxcomb in self.maxcomb]
            combos = [ak.from_regular(c) for c in combos]
            self.combos = combos

            pt = ak.concatenate([pt[comb] for pt,comb in zip(self.jet_ptRegressed,combos)])
            eta = ak.concatenate([eta[comb] for eta,comb in zip(self.jet_eta,combos)])
            phi = ak.concatenate([phi[comb] for phi,comb in zip(self.jet_phi,combos)])
            m = ak.concatenate([m[comb] for m,comb in zip(self.jet_mRegressed,combos)])
            btag = ak.concatenate([btag[comb] for btag,comb in zip(self.jet_btag,combos)])
        
        HX_b1 = Particle({'pt':pt[:,0],'eta':eta[:,0],'phi':phi[:,0],'m':m[:,0],'btag':btag[:,0]})
        HX_b2 = Particle({'pt':pt[:,1],'eta':eta[:,1],'phi':phi[:,1],'m':m[:,1],'btag':btag[:,1]})
        H1_b1 = Particle({'pt':pt[:,2],'eta':eta[:,2],'phi':phi[:,2],'m':m[:,2],'btag':btag[:,2]})
        H1_b2 = Particle({'pt':pt[:,3],'eta':eta[:,3],'phi':phi[:,3],'m':m[:,3],'btag':btag[:,3]})
        H2_b1 = Particle({'pt':pt[:,4],'eta':eta[:,4],'phi':phi[:,4],'m':m[:,4],'btag':btag[:,4]})
        H2_b2 = Particle({'pt':pt[:,5],'eta':eta[:,5],'phi':phi[:,5],'m':m[:,5],'btag':btag[:,5]})

        self.HX = HX_b1 + HX_b2
        self.H1 = H1_b1 + H1_b2
        self.H2 = H2_b1 + H2_b2

        self.HX.b1 = HX_b1
        self.HX.b2 = HX_b2
        self.H1.b1 = H1_b1
        self.H1.b2 = H1_b2
        self.H2.b1 = H2_b1
        self.H2.b2 = H2_b2

        self.Y = self.H1 + self.H2

        self.X = self.H1 + self.H2 + self.HX

        self.btag_avg = ak.mean(btag, axis=1)
        self.btag = btag

        # self.tight_mask  = ak.concatenate(self.btag) > self.tight_wp
        # medium_mask = ak.concatenate(self.btag) > self.medium_wp
        # loose_mask  = ak.concatenate(self.btag) > self.loose_wp

        # self.fail_mask = ~loose_mask
        # self.loose_mask = loose_mask & ~medium_mask
        # self.medium_mask = medium_mask & ~self.tight_mask

        # self.n_tight = ak.sum(self.tight_mask, axis=1)
        # self.n_medium = ak.sum(self.medium_mask, axis=1)
        # self.n_loose = ak.sum(self.loose_mask, axis=1)
        # self.n_fail = ak.sum(self.fail_mask, axis=1)


    def init_from_cuts(self):

        btag = ak.concatenate(self.jet_btag)
        self.btag_avg = ak.mean(btag, axis=1)

        HX_b1 = Particle({
            'pt':ak.concatenate(self.HX_b1_pt),
            'eta':ak.concatenate(self.HX_b1_eta),
            'phi':ak.concatenate(self.HX_b1_phi),
            'm':ak.concatenate(self.HX_b1_m),
            'btag':ak.concatenate(self.HX_b1_btag)})
        HX_b2 = Particle({
            'pt':ak.concatenate(self.HX_b2_pt),
            'eta':ak.concatenate(self.HX_b2_eta),
            'phi':ak.concatenate(self.HX_b2_phi),
            'm':ak.concatenate(self.HX_b2_m),
            'btag':ak.concatenate(self.HX_b2_btag)})
        H1_b1 = Particle({
            'pt':ak.concatenate(self.H1_b1_pt),
            'eta':ak.concatenate(self.H1_b1_eta),
            'phi':ak.concatenate(self.H1_b1_phi),
            'm':ak.concatenate(self.H1_b1_m),
            'btag':ak.concatenate(self.H1_b1_btag)})
        H1_b2 = Particle({
            'pt':ak.concatenate(self.H1_b2_pt),
            'eta':ak.concatenate(self.H1_b2_eta),
            'phi':ak.concatenate(self.H1_b2_phi),
            'm':ak.concatenate(self.H1_b2_m),
            'btag':ak.concatenate(self.H1_b2_btag)})
        H2_b1 = Particle({
            'pt':ak.concatenate(self.H2_b1_pt),
            'eta':ak.concatenate(self.H2_b1_eta),
            'phi':ak.concatenate(self.H2_b1_phi),
            'm':ak.concatenate(self.H2_b1_m),
            'btag':ak.concatenate(self.H2_b1_btag)})
        H2_b2 = Particle({
            'pt':ak.concatenate(self.H2_b2_pt),
            'eta':ak.concatenate(self.H2_b2_eta),
            'phi':ak.concatenate(self.H2_b2_phi),
            'm':ak.concatenate(self.H2_b2_m),
            'btag':ak.concatenate(self.H2_b2_btag)})
        
        self.HX = HX_b1 + HX_b2
        self.H1 = H1_b1 + H1_b2
        self.H2 = H2_b1 + H2_b2

        self.HX.b1 = HX_b1
        self.HX.b2 = HX_b2
        self.H1.b1 = H1_b1
        self.H1.b2 = H1_b2
        self.H2.b1 = H2_b1
        self.H2.b2 = H2_b2

        self.Y = self.H1 + self.H2

        self.X = self.H1 + self.H2 + self.HX

    def get_hist_weights(self, key, bins):
        if self.is_bkgd: 
            n = np.zeros_like(bins[:-1])
            for i,(sample, scale) in enumerate(zip(self.sample, self.scale)):
                try:
                    branch = ak.flatten(getattr(getattr(self, sample), key)).to_numpy()
                except:
                    branch = getattr(getattr(self, sample), key).to_numpy()
                n_i, b = np.histogram(branch, bins)
                centers = (b[1:] + b[:-1])/2
                n += n_i*scale
            return n#, b, centers
        else: 
            branch = ak.flatten(getattr(self, key)).to_numpy()
            n, b = np.histogram(branch, bins)
            centers = (b[1:] + b[:-1])/2
            # n_tot = sum(n)
            # epsilon = 5e-3
            # max_bin = sum(n > epsilon*n_tot) + 1
            # new_bins = np.linspace(branch.min(), bins[max_bin], 100)
            # n, b = np.histogram(branch, new_bins)
            # centers = (b[1:] + b[:-1])/2
        return n*self.scale#, b, centers

    def spherical_region(self, cfg='config/bdt_params.cfg', nregions='concentric'):
        self.cfg = cfg
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(self.cfg)
        self.config = self.config
        if nregions == 'multiple':
            print("REGION: multiple")
            self.multi_region()
        # elif self.config['spherical']['nregions'] == 'diagonal':
        elif nregions == 'diagonal':
            print("REGION: diagonal")
            self.diagonal_region()
        # elif self.config['spherical']['nregions'] == 'concentric':
        elif nregions == 'concentric':
            print("REGION: concentric")
            self.concentric_spheres_region()
    
    def concentric_spheres_region(self):
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(self.cfg)
        self.config = self.config

        minMX = int(self.config['plot']['minMX'])
        maxMX = int(self.config['plot']['maxMX'])
        if self.config['plot']['style'] == 'linspace':
            nbins = int(self.config['plot']['edges'])
            self.mBins = np.linspace(minMX,maxMX,nbins)
        if self.config['plot']['style'] == 'arange':
            step = int(self.config['plot']['steps'])
            self.mBins = np.arange(minMX,maxMX,step)

        self.x_mBins = (self.mBins[:-1] + self.mBins[1:])/2

        """Defines spherical estimation region masks."""
        self.ar_center = float(self.config['spherical']['ARcenter'])
        self.sr_edge   = float(self.config['spherical']['SRedge'])
        self.vr_edge   = float(self.config['spherical']['VRedge'])
        self.cr_edge   = float(self.config['spherical']['CRedge'])

        # higgs = ['HX_m', 'H1_m', 'H2_m']
        higgs = [self.HX.m, self.H1.m, self.H2.m]

        # deltaM = np.column_stack(([getattr(self, mH).to_numpy() - self.ar_center for mH in higgs]))
        deltaM = np.column_stack(([abs(mH - self.ar_center) for mH in higgs]))
        deltaM = deltaM * deltaM
        deltaM = deltaM.sum(axis=1)
        deltaM = np.sqrt(deltaM)

        self.asr_mask = deltaM <= self.sr_edge # Analysis SR
        self.A_SR_avgbtag = self.btag_avg[self.asr_mask]
        self.acr_mask = (deltaM > self.sr_edge) & (deltaM <= self.cr_edge) # Analysis CR
        self.A_CR_avgbtag = self.btag_avg[self.acr_mask]

        # vsr_edge = self.sr_edge*2 + self.cr_edge
        # vcr_edge = self.sr_edge*2 + self.cr_edge*2
        self.vsr_mask = (deltaM <= self.cr_edge) &  (deltaM > self.sr_edge)# Validation SR
        self.vcr_mask = (deltaM > self.cr_edge) & (deltaM <= self.vr_edge) # Validation CR

        self.score_cut = float(self.config['score']['threshold'])
        self.ls_mask = self.btag_avg < self.score_cut # ls
        self.hs_mask = self.btag_avg >= self.score_cut # hs


        # b_cut = float(config['score']['n'])
        # self.nloose_b = ak.sum(self.get('jet_btag') > 0.0490, axis=1)
        # self.nmedium_b = ak.sum(self.get('jet_btag') > 0.2783, axis=1)
        # ls_mask = self.nmedium_b < b_cut # ls
        # hs_mask = self.nmedium_b >= b_cut # hs

        self.acr_ls_mask = self.acr_mask & self.ls_mask
        self.acr_hs_mask = self.acr_mask & self.hs_mask
        self.asr_ls_mask = self.asr_mask & self.ls_mask
        self.asr_hs_mask = self.asr_mask & self.hs_mask
        # else: self.A_CR_avgbtag = self.btag_avg[self.vcr_mask]

        self.vcr_ls_mask = self.vcr_mask & self.ls_mask
        self.vcr_hs_mask = self.vcr_mask & self.hs_mask
        self.vsr_ls_mask = self.vsr_mask & self.ls_mask
        self.vsr_hs_mask = self.vsr_mask & self.hs_mask

    def multi_region(self):
        """
        The GNN tends to flatten out the 2D MH_i v. MH_j distribution, leaving fewer events in the validation region and posing a potential problem when it comes to obtaining closure. This function introduces more validation regions, which makes the validation plots look better... but now that I think about it, I'm changing the validation regions without affecting at all the signal region and estimation going on in there... How can I show with confidence that whatever validation region I use is a good representative of the signal region?

        Ultimately the goal is to apply the background modeling procedure in the validation region, show that it works, and obtain confidence that it will work in the signal region... but we should be able to show that the validation region is kinematically similar to the signal region, right? I'm not quite sure anymore.
        """
        self.config = ConfigParser()
        self.config.optionxform = str
        self.config.read(self.cfg)
        self.config = self.config

        minMX = int(self.config['plot']['minMX'])
        maxMX = int(self.config['plot']['maxMX'])
        if self.config['plot']['style'] == 'linspace':
            nbins = int(self.config['plot']['edges'])
            self.mBins = np.linspace(minMX,maxMX,nbins)
        if self.config['plot']['style'] == 'arange':
            step = int(self.config['plot']['steps'])
            self.mBins = np.arange(minMX,maxMX,step)

        self.x_mBins = (self.mBins[:-1] + self.mBins[1:])/2

        """Defines spherical estimation region masks."""
        self.ar_center = float(self.config['spherical']['ARcenter'])
        self.sr_edge   = float(self.config['spherical']['SRedge'])
        self.cr_edge   = float(self.config['spherical']['CRedge'])

        deltaS = (self.cr_edge + self.sr_edge) / np.sqrt(2)
        
        val_centers = []
        val_centers.append((self.ar_center + deltaS, self.ar_center + deltaS, self.ar_center + deltaS))
        val_centers.append((self.ar_center + deltaS, self.ar_center + deltaS, self.ar_center - deltaS))
        val_centers.append((self.ar_center + deltaS, self.ar_center - deltaS, self.ar_center + deltaS))
        val_centers.append((self.ar_center - deltaS, self.ar_center + deltaS, self.ar_center + deltaS))
        val_centers.append((self.ar_center + deltaS, self.ar_center - deltaS, self.ar_center - deltaS))
        val_centers.append((self.ar_center - deltaS, self.ar_center + deltaS, self.ar_center - deltaS))
        val_centers.append((self.ar_center - deltaS, self.ar_center - deltaS, self.ar_center + deltaS))
        val_centers.append((self.ar_center - deltaS, self.ar_center - deltaS, self.ar_center - deltaS))

        higgs = [self.HX.m, self.H1.m, self.H2.m]

        self.asr_mask, self.acr_mask = get_region_mask(higgs, (125,125,125), self.sr_edge, self.cr_edge)


        vsr_masks, vcr_masks = [], []
        self.vsr_mask = np.repeat(False, len(self.asr_mask))
        self.vcr_mask = np.repeat(False, len(self.asr_mask))
        for center in val_centers:
            vsr_mask, vcr_mask = get_region_mask(higgs, center, self.sr_edge, self.cr_edge)
            self.vsr_mask = np.logical_or(self.vsr_mask, vsr_mask)
            self.vcr_mask = np.logical_or(self.vcr_mask, vcr_mask)
            vsr_masks.append(vsr_mask)
            vcr_masks.append(vcr_mask)

        # print("vsr_mask:", self.vsr_mask)
        assert ak.any(self.vsr_mask), "No validation region found. :("

        self.score_cut = float(self.config['score']['threshold'])
        self.ls_mask = self.btag_avg < self.score_cut # ls
        self.hs_mask = self.btag_avg >= self.score_cut # hs

        self.acr_ls_mask = self.acr_mask & self.ls_mask
        self.acr_hs_mask = self.acr_mask & self.hs_mask
        self.asr_ls_mask = self.asr_mask & self.ls_mask
        self.asr_hs_mask = self.asr_mask & self.hs_mask
        # else: self.A_CR_avgbtag = self.btag_avg[self.vcr_mask]

        self.vcr_ls_masks, self.vcr_hs_masks = [], []
        self.vsr_ls_masks, self.vsr_hs_masks = [], []
        for vsr_mask, vcr_mask in zip(vsr_masks, vcr_masks):
            vcr_ls_mask, vcr_hs_mask, vsr_ls_mask, vsr_hs_mask = get_hs_ls_masks(vsr_mask, vcr_mask, self.ls_mask, self.hs_mask)

            self.vcr_ls_masks.append(vcr_ls_mask)
            self.vcr_hs_masks.append(vcr_hs_mask)
            self.vsr_ls_masks.append(vsr_ls_mask)
            self.vsr_hs_masks.append(vsr_hs_mask)

        
        self.vcr_ls_mask = np.any(self.vcr_ls_masks, axis=0)
        self.vcr_hs_mask = np.any(self.vcr_hs_masks, axis=0)
        self.vsr_ls_mask = np.any(self.vsr_ls_masks, axis=0)
        self.vsr_hs_mask = np.any(self.vsr_hs_masks, axis=0)

    def diagonal_region(self):
        
        minMX = int(self.config['plot']['minMX'])
        maxMX = int(self.config['plot']['maxMX'])
        if self.config['plot']['style'] == 'linspace':
            nbins = int(self.config['plot']['edges'])
            self.mBins = np.linspace(minMX,maxMX,nbins)
        if self.config['plot']['style'] == 'arange':
            step = int(self.config['plot']['steps'])
            self.mBins = np.arange(minMX,maxMX,step)

        self.x_mBins = (self.mBins[:-1] + self.mBins[1:])/2

        """Defines spherical estimation region masks."""
        self.ar_center = float(self.config['spherical']['ARcenter'])
        self.sr_edge   = float(self.config['spherical']['SRedge'])
        self.cr_edge   = float(self.config['spherical']['CRedge'])

        # higgs = ['HX_m', 'H1_m', 'H2_m']
        higgs = [self.HX.m, self.H1.m, self.H2.m]

        # deltaM = np.column_stack(([getattr(self, mH).to_numpy() - self.ar_center for mH in higgs]))
        deltaM = np.column_stack(([abs(mH.to_numpy() - self.ar_center) for mH in higgs]))
        deltaM = deltaM * deltaM
        deltaM = deltaM.sum(axis=1)
        AR_deltaM = np.sqrt(deltaM)
        self.asr_mask = AR_deltaM <= self.sr_edge # Analysis SR
        self.A_SR_avgbtag = self.btag_avg[self.asr_mask]
        self.acr_mask = (AR_deltaM > self.sr_edge) & (AR_deltaM <= self.cr_edge) # Analysis CR
        self.A_CR_avgbtag = self.btag_avg[self.acr_mask]

        # VR_deltaM = np.column_stack(([abs(getattr(self, mH).to_numpy() - self.vr_center) for mH in higgs]))
        VR_deltaM = np.column_stack(([abs(mH.to_numpy() - self.vr_center) for mH in higgs]))
        VR_deltaM = VR_deltaM * VR_deltaM
        VR_deltaM = VR_deltaM.sum(axis=1)
        VR_deltaM = np.sqrt(VR_deltaM)
        self.vsr_mask = VR_deltaM <= self.sr_edge # Validation SR
        self.vcr_mask = (VR_deltaM > self.sr_edge) & (VR_deltaM <= self.cr_edge) # Validation CR

        self.score_cut = float(self.config['score']['threshold'])
        self.ls_mask = self.btag_avg < self.score_cut # ls
        self.hs_mask = self.btag_avg >= self.score_cut # hs

        self.acr_ls_mask = self.acr_mask & self.ls_mask
        self.acr_hs_mask = self.acr_mask & self.hs_mask
        self.asr_ls_mask = self.asr_mask & self.ls_mask
        self.asr_hs_mask = self.asr_mask & self.hs_mask
        # else: self.A_CR_avgbtag = self.btag_avg[self.vcr_mask]

        self.vcr_ls_mask = self.vcr_mask & self.ls_mask
        self.vsr_ls_mask = self.vsr_mask & self.ls_mask
        self.vcr_hs_mask = self.vcr_mask & self.hs_mask
        self.vsr_hs_mask = self.vsr_mask & self.hs_mask