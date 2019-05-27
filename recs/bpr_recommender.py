import collections
import json
import pickle

import pandas as pd
from django.db.models import Avg

from analytics.models import Rating
from recs.base_recommender import base_recommender


class BPRRecs(base_recommender):
    def __init__(self, save_path='./models/bpr/'):
        self.save_path = save_path
        self.model_loaded = False
        self.avg = list(Rating.objects.all().aggregate(Avg('rating')).values())[0]

    def load_model(self, save_path):

        with open(save_path + 'item_bias.data', 'rb') as ub_file:
            self.item_bias = pickle.load(ub_file)
        with open(save_path + 'user_factors.json', 'r') as infile:
            self.user_factors = pd.DataFrame(json.load(infile)).T
        with open(save_path + 'item_factors.json', 'r') as infile:
            self.item_factors = pd.DataFrame(json.load(infile)).T
        self.ordered_item_bias = list(collections.OrderedDict(sorted(self.item_bias.items())).values())
        self.model_loaded = True

    def set_save_path(self, save_path):
        self.save_path = save_path

        self.load_model(save_path)

    def predict_score(self, user_id, item_id):

        if not self.model_loaded:
            self.load_model(self.save_path)

        return self.avg

    def recommend_items(self, user_id, num=6):

        if not self.model_loaded:
            self.load_model(self.save_path)

        active_user_items = Rating.objects.filter(user_id=user_id).order_by('-rating')[:100]

        return self.recommend_items_by_ratings(user_id, active_user_items.values())

    def recommend_items_by_ratings(self, user_id, active_user_items, num=6):

        if not self.model_loaded:
            self.load_model(self.save_path)

        rated_movies = {movie['movie_id']: movie['rating']
                        for movie in active_user_items}
        recs = {}
        if str(user_id) in self.user_factors.columns:
            user = self.user_factors[str(user_id)]

            scores = self.item_factors.T.dot(user)

            sorted_scores = scores.sort_values(ascending=False)
            result = sorted_scores[:num + len(rated_movies)]

            recs = {r[0]: {'prediction': r[1] + self.item_bias[r[0]]}
                    for r in zip(result.index, result)
                    if r[0] not in rated_movies}

        sorted_items = sorted(recs.items(),
                              key=lambda item: -float(item[1]['prediction']))

        return sorted_items[:num]
