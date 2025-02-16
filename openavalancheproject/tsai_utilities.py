# AUTOGENERATED! DO NOT EDIT! File to edit: ../DataPipelineNotebooks/4.TSAIUtilities.ipynb.

# %% auto 0
__all__ = ['TSAIUtilities']

# %% ../DataPipelineNotebooks/4.TSAIUtilities.ipynb 2
from pandas.api.types import CategoricalDtype
from joblib import Parallel, delayed
import os.path
import numpy as np
import pandas as pd
from tsai.all import * 
from .tsai_simple_transforms import * 
#from openavalancheproject.prep_ml import *

# %% ../DataPipelineNotebooks/4.TSAIUtilities.ipynb 3
class TSAIUtilities:
    def __init__(self, X, label):
        self.X = X
        self.num_features = X.shape[1]
        self.label = label

    def numba_calcs(self, np_data):
        feature_stds = np.std(np_data, axis=(0,2))
        feature_means = np.mean(np_data, axis=(0,2))
        return feature_stds, feature_means
        
    def calc_std_and_mean(self, data, sample_lower_bound, sample_upper_bound):
        feature_stds = []
        feature_means = []
        num = 10
        for i in range(0, data.shape[1], num):
            print('on ' + str(i))
            upper = i + num
            if upper > data.shape[1]:
                upper = data.shape[1]
            np_data = data[sample_lower_bound:sample_upper_bound,i:upper,:]
            np_data = np.nan_to_num(np_data)
            tmp_stds, tmp_means = self.numba_calcs(np_data)
            feature_stds.extend(tmp_stds)
            feature_means.extend(tmp_means)
        return feature_stds, feature_means

    def calc_min_max(self, data, sample_lower_bound, sample_upper_bound):
        feature_mins = []
        feature_maxs = []
        num = 10
        for i in range(0, data.shape[1], num):
            print('on ' + str(i))
            upper = i + num
            if upper > data.shape[1]:
                upper = data.shape[1]
            np_data = data[sample_lower_bound:sample_upper_bound,i:upper,:]
            np_data = np.nan_to_num(np_data)
            tmp_min = np.min(np_data, axis=(0,2))
            tmp_max = np.max(np_data, axis=(0,2))
            feature_mins.extend(tmp_min)
            feature_maxs.extend(tmp_max)
        return feature_mins, feature_maxs 

    def get_y_as_cat(self, y_df):
        #convert the labels to encoded values
        labels = y_df[self.label].unique()
        if 'Low' in labels:
            labels = ['Low', 'Moderate', 'Considerable', 'High']
        elif 'Low_Falling' in labels:
            lables = ['Low_Falling', 'Low_Flat', 
                      'Moderate_Falling', 'Moderate_Flat', 'Moderate_Rising', 
                      'Considerable_Falling', 'Considerable_Flat', 'Considerable_Rising',
                      'High_Falling', 'High_Flat', 'High_Rising']                    
        else:
            labels.sort()
        cat_type = CategoricalDtype(categories=labels, ordered=True)
        y_df[self.label + '_Cat'] = y_df[self.label].astype(cat_type)
        y = y_df[self.label + '_Cat'].cat.codes.values

        cat_dict = dict( enumerate(y_df[self.label + '_Cat'].cat.categories ) )
        return y, cat_dict

    @staticmethod 
    def filter_features(feature_list, only_var=False):
        #remove any prefixed with var
        feature_list = set([x for x in feature_list if 'var' not in x])
        feature_list = set([x for x in feature_list if 'ABSV' not in x])
        feature_list = set([x for x in feature_list if 'CLMR' not in x])
        feature_list = set([x for x in feature_list if 'HGT' not in x])
        feature_list = set([x for x in feature_list if 'PRES' not in x])
        feature_list = set([x for x in feature_list if 'CPOFP' not in x])
        feature_list = set([x for x in feature_list if 'HLCY' not in x])
        feature_list = set([x for x in feature_list if 'PV_EQ' not in x])
        feature_list = set([x for x in feature_list if 'ICEC' not in x])
        feature_list = set([x for x in feature_list if 'LAND' not in x])
        feature_list = set([x for x in feature_list if 'SPFH' not in x])
        feature_list = set([x for x in feature_list if 'DPT' not in x])
        feature_list = set([x for x in feature_list if 'TCDC' not in x])
        feature_list = set([x for x in feature_list if 'HINDEX' not in x])
        feature_list = set([x for x in feature_list if 'mabovemeansealevel' not in x])
        feature_list = set([x for x in feature_list if 'tropopause' not in x])
        if not only_var:
            #operate only on avg and sum
            feature_list = set([x for x in feature_list if 'min' not in x])
            feature_list = set([x for x in feature_list if 'max' not in x])

            #get cloud cover
            cloud_features = set([x for x in feature_list if 'TCDC' in x])
            feature_list -= cloud_features
            
            #get any surface levels
            surface_features = set([x for x in feature_list if 'surface' in x])
            feature_list = feature_list - surface_features            

            #get all wind
            ugrd_wind_features = set([x for x in feature_list if 'UGRD' in x])
            vgrd_wind_features = set([x for x in feature_list if 'VGRD' in x])
            wind_features = set(list(ugrd_wind_features) + list(vgrd_wind_features))
            feature_list -= wind_features
            wind_features = set([x for x in wind_features if 'aboveground' not in x])
            
            #get any relative to ground (except wind)
            aboveground_features = set([x for x in feature_list if 'aboveground' in x])
            feature_list = feature_list - aboveground_features
            
            feature_prefix = set([x.split('_')[0] for x in feature_list])
            pressure_features = []
            for p in feature_prefix:
                #get a random subset for the features defined by pressure level
                tmp = [x for x in feature_list if p in x]
                tmp2 = pd.Series(tmp).sample(frac=.1)
                #return tmp2
                pressure_features.extend(list(tmp2))
        
            l = list(surface_features) + list(aboveground_features) + list(pressure_features) + list(cloud_features) + list(wind_features)
            
            feature_list = l
        feature_list = list(feature_list)
        feature_list.sort()
        return feature_list
    
    def create_dls(self, X, y, feature_mins, feature_maxs, splits, sample_frac = 1, batch_size=64):
        splits_2 = (L(list(pd.Series(splits[0]).sample(frac=sample_frac).values)), L(list(pd.Series(splits[1]).sample(frac=sample_frac).values)))
        #create the dataset
        tfms = [None, [Categorize()]]
        dsets = TSDatasets(X, y, tfms=tfms, splits=splits_2, inplace=False)
        
        mins = feature_mins.astype(np.float32)
        maxs = feature_maxs.astype(np.float32)
        batch_tfms = [TSFilter(), TSSimpleNormalize(mins=mins, maxs=maxs), Nan2Value()]
        dls = TSDataLoaders.from_dsets(dsets.train, dsets.valid, bs=[batch_size], batch_tfms=batch_tfms, num_workers=4, inplace=False)
        return splits_2, dls
    
    def create_different_splits(self, y_df, valid_season = '18-19'):
        a = y_df[y_df['season']!=valid_season].index
        b = y_df[y_df['season']==valid_season].index
        splits = (L(list(pd.Series(a))).shuffle(), L(list(pd.Series(b))).shuffle())
        return splits
    
    
    def augment_labels_with_trends(self, all_label_file, labels, label_to_add_trend_info='Day1DangerAboveTreeline'):
        #note this removes labels from labels, ensure you reindex X and reset the labels index after running this  
        #add extra labels which also allow us to have labels which indicate the trend in the avy direction
        #the thought here is that predicting a rise or flat danger is usually easier than predicting when 
        #to lower the danger so seperating these in to seperate clases
       
        all_labels = pd.read_csv(all_label_file, low_memory=False,
                        dtype={'Day1Danger_OctagonAboveTreelineEast': 'object',
                                'Day1Danger_OctagonAboveTreelineNorth': 'object',
                                'Day1Danger_OctagonAboveTreelineNorthEast': 'object',
                                'Day1Danger_OctagonAboveTreelineNorthWest': 'object',
                                'Day1Danger_OctagonAboveTreelineSouth': 'object',
                                'Day1Danger_OctagonAboveTreelineSouthEast': 'object',
                                'Day1Danger_OctagonAboveTreelineSouthWest': 'object',
                                'Day1Danger_OctagonAboveTreelineWest': 'object',
                                'Day1Danger_OctagonBelowTreelineEast': 'object',
                                'Day1Danger_OctagonBelowTreelineNorth': 'object',
                                'Day1Danger_OctagonBelowTreelineNorthEast': 'object',
                                'Day1Danger_OctagonBelowTreelineNorthWest': 'object',
                                'Day1Danger_OctagonBelowTreelineSouth': 'object',
                                'Day1Danger_OctagonBelowTreelineSouthEast': 'object',
                                'Day1Danger_OctagonBelowTreelineSouthWest': 'object',
                                'Day1Danger_OctagonBelowTreelineWest': 'object',
                                'Day1Danger_OctagonNearTreelineEast': 'object',
                                'Day1Danger_OctagonNearTreelineNorth': 'object',
                                'Day1Danger_OctagonNearTreelineNorthEast': 'object',
                                'Day1Danger_OctagonNearTreelineNorthWest': 'object',
                                'Day1Danger_OctagonNearTreelineSouth': 'object',
                                'Day1Danger_OctagonNearTreelineSouthEast': 'object',
                                'Day1Danger_OctagonNearTreelineSouthWest': 'object',
                                'Day1Danger_OctagonNearTreelineWest': 'object',
                                'SpecialStatement': 'object',
                                'image_paths': 'object',
                                'image_types': 'object',
                                'image_urls': 'object'})
        
        all_labels = all_labels[all_labels[label_to_add_trend_info] != 'no-data']
        all_labels['parsed_date'] = pd.to_datetime(all_labels['Day1Date'], format='%Y%m%d')
        
        #ensure we are only using label data for regions we are looking at
        #return region_zones
        all_labels['UnifiedRegion'] = all_labels.apply(lambda x : PrepML.lookup_forecast_region(x['UnifiedRegion']), axis=1)        
                              
        all_labels = all_labels[all_labels['UnifiedRegion']!='Unknown region']
        
        #add a season column
        tmp = pd.DataFrame.from_records(all_labels['parsed_date'].apply(PrepML.date_to_season).reset_index(drop=True))
        all_labels.reset_index(drop=True, inplace=True)
        all_labels['season'] = tmp[1]
        
        labels_trends = pd.DataFrame()
        for r in labels['UnifiedRegion'].unique():
            region_df = all_labels[all_labels['UnifiedRegion']==r]
            season_labels = labels[labels['UnifiedRegion']==r]
            for s in labels['season'].unique():                
                region_season_df = region_df[region_df['season']==s]
                region_season_labels = season_labels[season_labels['season']==s]
                for i, row in region_season_labels.iterrows():
                    d = row['parsed_date']                    

                    prev_label_row = region_season_df[region_season_df['parsed_date'] == d - pd.Timedelta(days=1)]
                    if(len(prev_label_row) == 0):
                        #print('Couldnt find prev for ' + r + ' ' + s + ' ' + str(d) + ' len ' + str(len(prev_label_row)) + ' ' + str(region_season_df['parsed_date'] - pd.Timedelta(days=1)))
                        continue
                    lookup = {'Low':0, 'Moderate':1, 'Considerable':2, 'High':3, 'Extreme': 4}
                    prev = lookup[prev_label_row[label_to_add_trend_info].iloc[0]]
                    cur = lookup[row[label_to_add_trend_info]]
                    trend = '_Unknown'
                    if prev == cur:
                        trend = '_Flat'
                    elif prev < cur:
                        trend = '_Rising'
                    elif prev >  cur:
                        trend = '_Falling'

                    labels.loc[i, label_to_add_trend_info + 'WithTrend'] = row[label_to_add_trend_info] + trend
    
