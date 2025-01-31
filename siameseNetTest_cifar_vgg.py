import tensorflow as tf
import numpy as np
import pickle
from tensorflow.keras.preprocessing import image
import time

start_time = time.time()

def contrastive_loss(y_true, y_pred, margin=1):
    y_true = tf.cast(y_true, y_pred.dtype)
    square_pred = tf.square(y_pred)
    margin_square = tf.square(tf.maximum(margin - y_pred, 0))
    return tf.reduce_mean(y_true * square_pred + (1 - y_true) * margin_square)

# Load the saved Siamese network model with VGG as the base
siamese_network = tf.keras.models.load_model('siamese_network_vgg_cifar10.h5', custom_objects={'contrastive_loss': contrastive_loss})

# Function to preprocess a single image
def preprocess_image(img):
    img = np.expand_dims(img, axis=0)  # Add batch dimension
    img = img / 255.0  # Normalize the image to [0, 1]
    return img

# Load the image pairs from the pickle file
with open('cifar10_image_pairs_test.pkl', 'rb') as f:
    image_pairs_test = pickle.load(f)

# Function to predict similarity for the pairs in the test set
def predict_similarity_for_pairs(image_pairs_test):
    total = len(image_pairs_test)
    print(f"Total pairs to test: {total}")
    similarities = []
    
    for idx, pair in enumerate(image_pairs_test):
        img1, img2, actual_label = pair  # Extract the pair and the actual label
        
        # Preprocess the images
        img1_preprocessed = preprocess_image(img1)
        img2_preprocessed = preprocess_image(img2)
        
        # Predict similarity
        similarity_score = siamese_network.predict([img1_preprocessed, img2_preprocessed])[0][0]
        
        similarities.append((similarity_score, actual_label))
        
        print(f"Pair {idx + 1}/{total} - sim: {similarity_score:.4f}, label: {actual_label}")
    
    # Convert the list to a NumPy array
    similarity_array = np.array(similarities)
    save_path = 'cosine_sim/cosine_sim_siameseNet_vgg_cifar10.npy'
    # Save the array to a file
    np.save(save_path, similarity_array)
    print(f"Cosine similarities saved to {save_path}")
    

# Predict similarity on the test pairs
predict_similarity_for_pairs(image_pairs_test)
end_time = time.time()
elapsed_time = end_time - start_time
print(f"Prediction completed in {elapsed_time // 60:.0f}m {elapsed_time % 60:.0f}s")
