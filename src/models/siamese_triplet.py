import torch
import torch.nn as nn
import pytorch_lightning as pl


class SiameseTriplet(pl.LightningModule):
    def __init__(self, embedding_dim=120, margin=1.0, learning_rate=0.001):
        super(SiameseTriplet, self).__init__()

        self.validation_step_outputs = []
        self.train_step_outputs = []

        # Fully connected layers for prediction
        self.fc_query = nn.Linear(embedding_dim, 256)
        self.fc_doc = nn.Linear(embedding_dim, 256)
        self.fc1 = nn.Linear(256, 128)
        self.fc2 = nn.Linear(128, 1)

        self.margin = margin
        self.learning_rate = learning_rate
        self.criterion = nn.TripletMarginLoss(margin=margin)

    def forward_one(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.sigmoid(self.fc2(x))
        return x

    def forward(self, anchor, positive, negative):
        anchor_embedding = self.forward_one(self.fc_query(anchor))
        positive_embedding = self.forward_one(self.fc_doc(positive))
        negative_embedding = self.forward_one(self.fc_doc(negative))
        
        return anchor_embedding, positive_embedding, negative_embedding

    def training_step(self, batch, batch_idx):
        anchor, positive, negative = batch
        out_anchor, out_positive, out_negative = self(anchor, positive, negative)
        loss = self.criterion(out_anchor, out_positive, out_negative)
        self.train_step_outputs.append(loss)
        return loss

    def validation_step(self, batch, batch_idx):
        anchor, positive, negative = batch
        out_anchor, out_positive, out_negative = self(anchor, positive, negative)
        loss = self.criterion(out_anchor, out_positive, out_negative)
        self.validation_step_outputs.append(loss)
        return loss

    def on_validation_epoch_end(self):
        if not len(self.train_step_outputs) == 0:
            epoch_average_train = torch.stack(self.train_step_outputs).mean()
            self.log("train_epoch_average", epoch_average_train)
            print("train_loss_avg: ", epoch_average_train)
            self.train_step_outputs.clear()
        if not len(self.validation_step_outputs) == 0:
            epoch_average = torch.stack(self.validation_step_outputs).mean()
            self.log("validation_epoch_average", epoch_average)
            print("val_loss_avg: ", epoch_average)
            self.validation_step_outputs.clear()


    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        return optimizer


class SiameseNetworkPL(pl.LightningModule):
    def __init__(self, embedding_size, learning_rate=1e-3, margin=1.0):
        super(SiameseNetworkPL, self).__init__()

        # Network architecture
        self.network = nn.Sequential(
            nn.Linear(embedding_size, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_size)
        )

        self.learning_rate = learning_rate
        self.triplet_loss = nn.TripletMarginLoss(margin=margin)

    def forward(self, x):
        # Forward pass for one input
        return self.network(x)

    def training_step(self, batch, batch_idx):
        # Training step
        anchor, positive, negative = batch
        anchor_output = self.forward(anchor)
        positive_output = self.forward(positive)
        negative_output = self.forward(negative)

        # Calculate triplet loss
        loss = self.triplet_loss(anchor_output, positive_output, negative_output)
        return loss

    def validation_step(self, batch, batch_idx):
        # Validation step, similar to training_step
        anchor, positive, negative = batch
        anchor_output = self.forward(anchor)
        positive_output = self.forward(positive)
        negative_output = self.forward(negative)

        # Calculate loss
        loss = self.triplet_loss(anchor_output, positive_output, negative_output)
        return {'val_loss': loss}

    def on_validation_epoch_end(self, outputs):
        # Aggregate validation loss
        avg_loss = torch.stack([x['val_loss'] for x in outputs]).mean()
        self.log('avg_val_loss', avg_loss)

    def configure_optimizers(self):
        # Configure optimizers
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        return optimizer