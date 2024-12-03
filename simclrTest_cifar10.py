import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from tensorflow.keras.models import load_model
import tensorflow_hub as hub
import pickle
from sklearn.preprocessing import normalize
import tensorflow as tf
import time


# Function to preprocess a CIFAR-10 image array
def preprocess_image(img_array):
    img_array = np.array(img_array) / 255.0  # Normalize the image
    img_array = tf.image.resize(img_array, (224, 224))  # Resize to match model input
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    return img_array

# Function to get feature vector for an image
def get_feature_vector(model, img_array):
    img = preprocess_image(img_array)
    feature_vector = model.predict(img)
    return feature_vector

# Compare two images and return cosine similarity
def compare_images(model, img_array1, img_array2):
    feature_vector1 = get_feature_vector(model, img_array1)
    feature_vector2 = get_feature_vector(model, img_array2)
    
    # Normalize feature vectors
    feature_vector1 = normalize(feature_vector1)
    feature_vector2 = normalize(feature_vector2)

    # Calculate cosine similarity
    similarity = cosine_similarity(feature_vector1, feature_vector2)
    return similarity[0][0]  # Return the similarity score

# Function to compute accuracy
def calculate_accuracy(model, image_pairs, threshold=0.5, save_path='cosine_sim/cosine_sim_simclr_cifar10.npy'):
    cosine_sim = []
    for img_array1, img_array2, label in image_pairs:
        similarity = compare_images(model, img_array1, img_array2)
        cosine_sim.append((similarity, label))
    
    # Convert the list to a NumPy array
    cosine_sim_array = np.array(cosine_sim)

    # Save the array to a file
    np.save(save_path, cosine_sim_array)
    print(f"Cosine similarities saved to {save_path}")


# Main execution block
if __name__ == "__main__":
    start_time = time.time()
    # Load the model
    model = load_model('model/simclr_preTrain_cifar10.h5', custom_objects={'KerasLayer': hub.KerasLayer})
    print("Model loaded successfully.")

    with open('cifar10_image_pairs_test.pkl', 'rb') as f:
        image_pairs_test = pickle.load(f)
        
    # Calculate accuracy for the model
    calculate_accuracy(model, image_pairs_test)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
