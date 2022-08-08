import awkward as ak
import numpy as np
np.seterr(all="ignore")
import vector
vector.register_awkward()

class Particle():
    def __init__(self, tree=None, particle_name=None, particle=None):
        """A class much like the TLorentzVector objects in the vector module but with more customizability for my analysis
        """

        if tree is not None and particle_name is not None:
            self.initialize_from_tree(tree, particle_name)
        elif particle is not None:
            self. initialize_from_particle(particle)
        self.P4 = self.get_vector()

    def initialize_from_tree(self, tree, particle_name):
        self.pt = tree.get(particle_name + '_pt')
        # self.ptRegressed = tree.get(particle_name + '_ptRegressed')
        self.eta = tree.get(particle_name + '_eta')
        self.phi = tree.get(particle_name + '_phi')
        self.m = tree.get(particle_name + '_m')
        self.theta = ak.from_numpy(2*np.arctan(np.exp(-self.eta.to_numpy())))
        self.cosTheta = np.cos(self.theta)

    def initialize_from_particle(self, particle):
        self.pt = particle.pt
        self.eta = particle.eta
        self.phi = particle.phi
        self.m = particle.m
        self.theta = ak.from_numpy(2*np.arctan(np.exp(-self.eta.to_numpy())))
        self.cosTheta = np.cos(self.theta)

    def get_vector(self):
        p4 = vector.obj(
            pt  = self.pt,
            eta = self.eta,
            phi = self.phi,
            m   = self.m
        )
        return p4

    def __add__(self, another_particle):
        particle1 = self.P4
        particle2 = another_particle.P4
        parent = particle1 + particle2
        return Particle(particle=parent)
    
    def boost(self, another_particle):
        return self.P4.boost(-another_particle.P4)

    def deltaEta(self, another_particle):
        return self.P4.deltaeta(another_particle.P4)

    def deltaPhi(self, another_particle):
        return self.P4.deltaphi(another_particle.P4)

    def deltaR(self, another_particle):
        return self.P4.deltaR(another_particle.P4)