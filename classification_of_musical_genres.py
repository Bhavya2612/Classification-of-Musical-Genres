# -*- coding: utf-8 -*-
"""classification of musical genres

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/120gLDsZu6V7R_7fIBCko5HOBfcQbkChW
"""

import pandas as pd
import tensorflow as tf
from IPython.display import Audio
import os
import matplotlib.pyplot as plt
import numpy as np
import math
import sys
from datetime import datetime
import pickle
import librosa
import ast
import scipy
import librosa.display
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow import keras
from google.colab import files

keras.backend.clear_session()
tf.random.set_seed(42)
np.random.seed(42)

from google.colab import drive
drive.mount('/content/drive')

# load the metadata to Colab from Drive, will greatly speed up the I/O process
zip_path_metadata = "/content/drive/My Drive/master_degree/machine_learning/Project/fma_metadata.zip"
!cp "{zip_path_metadata}" .
!unzip -q fma_metadata.zip
!rm fma_metadata.zip

# authenticate for GCS access
if 'google.colab' in sys.modules:
  from google.colab import auth
  auth.authenticate_user()

AUTO = tf.data.experimental.AUTOTUNE # used in tf.data.Dataset API
GCS_PATTERN = 'gs://music-genre-classification-project-isye6740/fma_small_wav/*/*.wav'
GCS_OUTPUT_1D = 'gs://music-genre-classification-project-isye6740/tfrecords-wav-1D/songs'  # prefix for output file names, first type of model
GCS_OUTPUT_2D = 'gs://music-genre-classification-project-isye6740/tfrecords-wav-2D/songs'  # prefix for output file names, second type of model
GCS_OUTPUT_FEATURES = 'gs://music-genre-classification-project-isye6740/tfrecords-features/songs' # prefix for output file names, models built with extracted features
SHARDS = 16
window_size = 10000 # number of raw audio samples
length_size_2d = 50176 # number of data points to form the Mel spectrogram
feature_size = 85210 # size of the feature vector
N_CLASSES = 8
DATA_SIZE = (224,224,3) # required data size for transfer learnin

def metadata_load(filepath):

    filename = os.path.basename(filepath)

    if 'features' in filename:
        return pd.read_csv(filepath, index_col=0, header=[0, 1, 2])

    if 'echonest' in filename:
        return pd.read_csv(filepath, index_col=0, header=[0, 1, 2])

    if 'genres' in filename:
        return pd.read_csv(filepath, index_col=0)

    if 'tracks' in filename:
        tracks = pd.read_csv(filepath, index_col=0, header=[0, 1])

        COLUMNS = [('track', 'tags'), ('album', 'tags'), ('artist', 'tags'),
                   ('track', 'genres'), ('track', 'genres_all')]
        for column in COLUMNS:
            tracks[column] = tracks[column].map(ast.literal_eval)

        COLUMNS = [('track', 'date_created'), ('track', 'date_recorded'),
                   ('album', 'date_created'), ('album', 'date_released'),
                   ('artist', 'date_created'), ('artist', 'active_year_begin'),
                   ('artist', 'active_year_end')]
        for column in COLUMNS:
            tracks[column] = pd.to_datetime(tracks[column])

        SUBSETS = ('small', 'medium', 'large')
        try:
            tracks['set', 'subset'] = tracks['set', 'subset'].astype(
                    pd.CategoricalDtype(categories=SUBSETS, ordered=True))
        except ValueError:
            # the categories and ordered arguments were removed in pandas 0.25
            tracks['set', 'subset'] = tracks['set', 'subset'].astype(
                     pd.CategoricalDtype(categories=SUBSETS, ordered=True))

        COLUMNS = [('track', 'genre_top'), ('track', 'license'),
                   ('album', 'type'), ('album', 'information'),
                   ('artist', 'bio')]
        for column in COLUMNS:
            tracks[column] = tracks[column].astype('category')

        return tracks

# function to get genre information for each track ID
def track_genre_information(GENRE_PATH, TRACKS_PATH, subset):
    """
    GENRE_PATH (str): path to the csv with the genre metadata
    TRACKS_PATH (str): path to the csv with the track metadata
    FILE_PATHS (list): list of paths to the mp3 files
    subset (str): the subset of the data desired
    """
    # get the genre information
    genres = pd.read_csv(GENRE_PATH)

    # load metadata on all the tracks
    tracks = metadata_load(TRACKS_PATH)

    # focus on the specific subset tracks
    subset_tracks = tracks[tracks['set', 'subset'] <= subset]

    # extract track ID and genre information for each track
    subset_tracks_genre = np.array([np.array(subset_tracks.index), 
                                  np.array(subset_tracks['track', 'genre_top'])]).T

    # combine the information in a dataframe
    tracks_genre_df = pd.DataFrame({'track_id': subset_tracks_genre[:,0], 'genre': subset_tracks_genre[:,1]})
    
    # label classes with numbers
    encoder = LabelEncoder()
    tracks_genre_df['genre_nb'] = encoder.fit_transform(tracks_genre_df.genre)
    
    return tracks_genre_df

# get genre information for all tracks from the small subset
GENRE_PATH = "fma_metadata/genres.csv"
TRACKS_PATH = "fma_metadata/tracks.csv"
subset = 'small'

small_tracks_genre = track_genre_information(GENRE_PATH, TRACKS_PATH, subset)

