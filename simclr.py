import os
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from sklearn.metrics import accuracy_score

# Set up your dataset path
dataset_path = 'flowers'  

# Load the dataset using ImageDataGenerator
batch_size = 64
datagen = ImageDataGenerator(rescale=1./255, validation_split=0.2)

# Use flow_from_directory to load the images from the directory
train_generator = datagen.flow_from_directory(
    dataset_path,
    target_size=(224, 224),
    batch_size=batch_size,
    class_mode='sparse',
    subset='training' 
)

# Create a validation generator
validation_generator = datagen.flow_from_directory(
    dataset_path,
    target_size=(224, 224),
    batch_size=batch_size,
    class_mode='sparse',
    subset='validation' 
)

# Getting number of classes
num_classes = train_generator.num_classes

# Load the SimCLR model as a Keras layer
hub_path = 'gs://simclr-checkpoints/simclrv2/finetuned_100pct/r50_1x_sk0/hub/'
module = hub.KerasLayer(hub_path, input_shape=(224, 224, 3), trainable=False)

# Define the fine-tuning process
def create_model():
    inputs = tf.keras.Input(shape=(224, 224, 3))
    base_model = module(inputs)  # Call the Keras layer with inputs
    outputs = tf.keras.layers.Dense(num_classes, activation='softmax')(base_model)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    return model

# Create and compile the model
model = create_model()
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

# Fine-tune the model
total_iterations = 10
history = model.fit(train_generator, 
                    validation_data=validation_generator, 
                    epochs=total_iterations)

# Save the model
model.save('model/simclr_preTrain_flower.h5')
print("Model saved as model/simclr_preTrain_flower.h5")

# Calculate accuracy
accuracy = model.evaluate(train_generator)[1]
print(f"Training Accuracy: {accuracy:.4f}")

# Evaluate on validation set
val_accuracy = model.evaluate(validation_generator)[1]
print(f"Validation Accuracy: {val_accuracy:.4f}")

# Function to extract features from images
def extract_features(generator):
    features = []
    labels = []
    
    for _ in range(len(generator)):
        x_batch, y_batch = generator.next()
        feature_batch = model.predict(x_batch)
        features.append(feature_batch)
        labels.append(y_batch)
    
    return np.concatenate(features), np.concatenate(labels)

# Extract features from validation set
val_features, val_labels = extract_features(validation_generator)

