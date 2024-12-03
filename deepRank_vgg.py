import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset, random_split
from torch.cuda.amp import GradScaler, autocast
from torchvision.models import vgg16
from PIL import Image
import torch.nn.functional as F

# Set random seeds for reproducibility
random.seed(42)
torch.manual_seed(42)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(42)

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Define image transformations
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Custom Dataset for Triplet Loss
class TripletImageDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.image_paths = []
        self.labels = []

        # Load images and labels
        for label in os.listdir(root_dir):
            class_dir = os.path.join(root_dir, label)
            if os.path.isdir(class_dir):
                for img in os.listdir(class_dir):
                    self.image_paths.append(os.path.join(class_dir, img))
                    self.labels.append(label)

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        anchor_path = self.image_paths[idx]
        anchor_label = self.labels[idx]

        # Choose a positive sample (same class)
        positive_idx = random.choice([i for i in range(len(self.image_paths)) if self.labels[i] == anchor_label and i != idx])
        positive_path = self.image_paths[positive_idx]

        # Choose a negative sample (different class)
        negative_idx = random.choice([i for i in range(len(self.image_paths)) if self.labels[i] != anchor_label])
        negative_path = self.image_paths[negative_idx]

        anchor = Image.open(anchor_path).convert("RGB")
        positive = Image.open(positive_path).convert("RGB")
        negative = Image.open(negative_path).convert("RGB")

        if self.transform:
            anchor = self.transform(anchor)
            positive = self.transform(positive)
            negative = self.transform(negative)

        return anchor, positive, negative

# Function to calculate accuracy
def calculate_similarity_accuracy(anchor_output, positive_output, negative_output):
    # Distance between anchor and positive
    pos_dist = F.pairwise_distance(anchor_output, positive_output)
    # Distance between anchor and negative
    neg_dist = F.pairwise_distance(anchor_output, negative_output)
    # Check if anchor is closer to positive than negative
    return (pos_dist < neg_dist).float().mean().item()

# Load dataset
directory = 'flowers/'
dataset = TripletImageDataset(directory, transform=transform)

# Split the dataset into training and validation sets (80% training, 20% validation)
train_size = int(0.8 * len(dataset))
val_size = len(dataset) - train_size
train_dataset, val_dataset = random_split(dataset, [train_size, val_size])

train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)
val_loader = DataLoader(val_dataset, batch_size=8, shuffle=False)

# Initialize VGG model, modify it for our use
class VGGModel(nn.Module):
    def __init__(self):
        super(VGGModel, self).__init__()
        self.base_model = vgg16(pretrained=True)
        # Remove the classifier layer and keep only the feature extractor part
        self.base_model.classifier = nn.Identity()
        
    def forward(self, x):
        x = self.base_model(x)
        return x

model = VGGModel().to(device)
criterion = nn.TripletMarginLoss()
optimizer = optim.Adam(model.parameters(), lr=0.0001)

# Initialize GradScaler for mixed precision training
scaler = GradScaler()

# Training and validation function
def train_model(num_epochs, save_path):
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        train_accuracy = 0.0
        for anchor, positive, negative in train_loader:
            anchor, positive, negative = anchor.to(device), positive.to(device), negative.to(device)

            optimizer.zero_grad()

            with autocast(enabled=torch.cuda.is_available()):
                anchor_output = model(anchor)
                positive_output = model(positive)
                negative_output = model(negative)
                loss = criterion(anchor_output, positive_output, negative_output)

            # Scale the loss and backpropagate
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item()
            train_accuracy += calculate_similarity_accuracy(anchor_output, positive_output, negative_output)

        # Calculate average loss and accuracy for the epoch
        avg_loss = running_loss / len(train_loader)
        avg_train_acc = train_accuracy / len(train_loader)

        # Validation step
        model.eval()
        val_accuracy = 0.0
        with torch.no_grad():
            for anchor, positive, negative in val_loader:
                anchor, positive, negative = anchor.to(device), positive.to(device), negative.to(device)

                anchor_output = model(anchor)
                positive_output = model(positive)
                negative_output = model(negative)

                val_accuracy += calculate_similarity_accuracy(anchor_output, positive_output, negative_output)

        avg_val_acc = val_accuracy / len(val_loader)

        print(f"Epoch [{epoch + 1}/{num_epochs}], Loss: {avg_loss:.4f}, "
              f"Train Similarity Accuracy: {avg_train_acc:.4f}, Validation Similarity Accuracy: {avg_val_acc:.4f}")

        # Optionally clear cache to manage memory
        torch.cuda.empty_cache()

    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")

model_path = "model/deeprank_vgg.pth"
num_epochs = 10
# Train the model
train_model(num_epochs, model_path)
