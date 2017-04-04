#This is the core classification algorithm. To be called from Classify.py and Plot.py

import os, sys, shutil, subprocess, getopt
from itertools import *
from multiprocessing import Pool, freeze_support
import numpy as np
import h5py
import numpy.matlib
import scipy.optimize


def Classify(training_file_names, CKM_matrices, Y_norms, cutoff):
	# file_base_name = os.path.basename(input_file_name)
	thresholds = [.90,.80,.70,.60,.50,.40,.30,.20,.10]
	kmer_sizes = [30, 50]

	# Make hypothetical matrices
	A_with_hypotheticals = list()
	for kmer_size in kmer_sizes:
		A = CKM_matrices[kmer_sizes.index(kmer_size)]
		A_norm = A/np.diag(A)
		# Create hypothetical organisms
		hypothetical_matrix = np.zeros((np.size(A_norm,0),len(thresholds)*np.size(A_norm,1)), dtype=np.float64)
		if kmer_sizes.index(kmer_size)>0:
			temp_thresholds = [-.5141*(val**3)+1.0932*(val**2)+0.3824*val for val in thresholds]
		else:
			temp_thresholds = [val for val in thresholds]
		for threshold in temp_thresholds:
			for organism_index in range(np.size(A_norm,1)):
				hyp_organism_vect = np.array(A_norm[:,organism_index], dtype=np.float64)
				hyp_organism_vect[hyp_organism_vect > threshold] = threshold #Instead of rounding down, we might apply the best fit polynomial to each entry of the vector
				hypothetical_matrix[:, organism_index + (np.size(A_norm,1)*temp_thresholds.index(threshold))] = hyp_organism_vect
		A_with_hypotheticals.append(np.concatenate((A_norm,hypothetical_matrix), axis=1))
		hypothetical_matrix = []
		A = []

	A_with_hypotheticals = np.concatenate(A_with_hypotheticals, axis=0)

	# Reduce basis
	basis = Y_norms[kmer_sizes.index(min(kmer_sizes))] > cutoff
	if not any(basis):
		print("Error: no organisms detected. Most likely sequencing depth is too low, or error rate is too high")
		sys.exit(2)
	
	y = np.concatenate([Y_norms[i][basis] for i in range(len(Y_norms))])
	column_basis = np.matlib.repmat(basis, 1, len(thresholds)+1).flatten()
	# Non-sparsity promoting
	# xtemp = scipy.optimize.nnls(A_with_hypothetical[np.concatenate(tuple(basis for i in range(len(kmer_sizes))),axis=0),:][:,column_basis],y)[0]

	# Sparsity promoting
	# Reduce the A basis
	# A_with_hypotheticals = A_with_hypotheticals[np.concatenate(tuple(basis for i in range(len(kmer_sizes))), axis=0), :][:, column_basis]

	# A better way that just selects the rows/columns we want
	A_with_hypotheticals = A_with_hypotheticals[np.ix_(np.concatenate(tuple(basis for i in range(len(kmer_sizes))), axis=0), column_basis)]

	lam = 200

	# Add the row of 1's on the top and the lam A. This is A_tilde
	A_with_hypotheticals = np.concatenate((np.ones((1, A_with_hypotheticals.shape[1])), lam * A_with_hypotheticals))
	y_tilde = np.concatenate((np.zeros(1), lam * y))

	# xtemp = scipy.optimize.nnls(np.concatenate((np.ones((1,Atemp.shape[1])),lam*Atemp)),np.concatenate((np.zeros(1),lam*y)))[0]

	# res = scipy.optimize.lsq_linear(np.concatenate((np.ones((1,Atemp.shape[1])),lam*Atemp)),np.concatenate((np.zeros(1),lam*y)), bounds=(0,np.inf), method='bvls', verbose=0)

	res = scipy.optimize.lsq_linear(A_with_hypotheticals, y_tilde, bounds=(0, 1), method='bvls', max_iter=700, verbose=0)
	xtemp = res.x
	
	# Sometimes there are entries very close to zero, but negative. Remove them
	for i in range(len(xtemp)):
		if xtemp[i] < 0:
			xtemp[i] = 0


	#create vector on full basis
	x = np.zeros(len(training_file_names)*(len(thresholds)+1))

	#populate with the reconstructed frequencies
	x[column_basis] = xtemp

	#return x vector
	return x





