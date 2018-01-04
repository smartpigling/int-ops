from django.test import TestCase

# Create your tests here.
import pickle
print(pickle.dumps(0, pickle.HIGHEST_PROTOCOL))