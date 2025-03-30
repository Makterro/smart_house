import gc
import os
import sys
from abc import abstractmethod

import torch.optim.lr_scheduler
import torchmetrics
from tqdm import tqdm
from torch.utils.tensorboard import SummaryWriter


class Trainer:
    def __init__(
            self, model,
            train_loader, val_loader, val_per_epoch,
            output_path, seq_len, num_classes,
            initial_lr, minimal_lr,
            device="cuda",
            optimizer_state_dict=None
    ) -> None:
        print("Initializing trainer...")

        self.train_loader = train_loader
        self.val_loader = val_loader

        self.model = model
        self.optimizer = None
        self.scheduler = None
        self.criterion = None

        self.ignore_first_epochs = 0
        self.save_every_n_epochs = 10
        self.rank_every_n_epochs = 5
        self.best_result = 0.

        self.minimal_lr = minimal_lr

        self.load_optimizer(initial_lr, optimizer_state_dict)
        self.load_scheduler(minimal_lr)

        self._set_output_path(output_path)

        self.device = device

        self.metrics_single_value = {
            "F1": torchmetrics.F1Score("multiclass", num_classes=num_classes).to(device),
            "Accuracy": torchmetrics.Accuracy("multiclass", num_classes=num_classes).to(device)
        }

        self.steps_per_epoch = len(train_loader)
        self.steps_per_validation = self.steps_per_epoch / val_per_epoch
        self.next_val_step = self.steps_per_validation

        self.metrics = set(self.metrics_single_value.values())
        self.reset_metrics()

        self.writers = [
            SummaryWriter(comment="train", log_dir=os.path.join(self.log_path, "train")),
            SummaryWriter(comment="val", log_dir=os.path.join(self.log_path, "val"))
        ]

        print(f"Console command: tensorboard  --bind_all --logdir {self.log_path}")

    def load_optimizer(self, learning_rate, optimizer_state_dict=None):
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate, weight_decay=.0001)

        if optimizer_state_dict is not None:
            self.optimizer.load_state_dict(optimizer_state_dict)

    def load_scheduler(self, minimal_lr):
        self.scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=10, gamma=.95)
        # self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=10, eta_min=minimal_lr)

    def scheduler_step(self) -> float:
        self.scheduler.step()

        return self.scheduler.get_last_lr()[0]

    def reset_metrics(self):
        for metric in self.metrics:
            metric.reset()

    def write_current_metrics(self, writer_index, global_step_index):
        for metric_name, metric in self.metrics_single_value.items():
            metric_value = metric.compute()
            self.writers[writer_index].add_scalar(f"{metric_name}", metric_value, global_step_index)

    def _predict(self, x):
        batch_size, seq_len, lms, dims = x.shape
        # return self.model(x.view(batch_size, -1))
        return self.model(x)

    def process_batch(self, x, y_true) -> float:
        y_pred = self._predict(x)

        loss = self.criterion(y_pred, y_true)
        for metric in self.metrics:
            metric.update(y_pred, y_true)

        loss.backward()
        self.optimizer.step()

        loss_value = loss.item()

        return loss_value

    def validation_step(self, i_step_global):
        self.reset_metrics()

        with torch.no_grad():
            for x, y_true in self.val_loader:
                x = x.to('cuda')
                y_true = y_true.to('cuda')

                y_pred = self._predict(x)

                for metric in self.metrics:
                    metric.update(y_pred, y_true)

                del y_pred

        self.write_current_metrics(1, i_step_global)

    @staticmethod
    def print_cuda_memory():
        free_mem, available_mem = torch.cuda.mem_get_info()

        bytes_per_gb = 1024**3

        print(f"Available memory: {free_mem / bytes_per_gb:.2f} / {available_mem / bytes_per_gb:.2f}")

    def process_epoch(self, i_epoch):
        # print(f"Epoch {i_epoch}")

        i_step_global = i_epoch * self.steps_per_epoch
        self.writers[0].add_scalar("Epoch", i_epoch, i_step_global)

        for i_step_local, batch in enumerate(tqdm(self.train_loader)):
            i_step_global = i_epoch * self.steps_per_epoch + i_step_local
            x, y = batch
            x = x.cuda()
            y = y.cuda()

            self.optimizer.zero_grad()

            epoch_loss = self.process_batch(x, y)

            torch.cuda.empty_cache()
            gc.collect()

            self.writers[0].add_scalar("Loss", epoch_loss, i_step_global)

            if i_step_global >= self.next_val_step:
                self.write_current_metrics(0, i_step_global)

                self.validation_step(i_step_global)
                self.next_val_step += self.steps_per_validation

        current_lr = self.scheduler_step()
        self.writers[1].add_scalar("LR", current_lr, i_step_global)
        self.writers[0].add_scalar("Epoch", i_epoch, i_step_global)

        if (i_epoch % self.save_every_n_epochs) == 0 and i_epoch > self.ignore_first_epochs:
            self.save_checkpoint(f"E{i_epoch}S{i_step_global}")

    def finish_training(self):
        for writer in self.writers:
            writer.close()

    def train(self, num_epochs, criterion):
        self.criterion = criterion

        if self.ignore_first_epochs:
            print(f"Training won't save first {self.ignore_first_epochs} epochs")

        print(f"Initiating training: {num_epochs} epochs; {self.steps_per_epoch} steps per epoch; "
              f"validation each {self.steps_per_validation:.2f} steps; ")

        self.model.to(self.device)

        for i_epoch in range(num_epochs):
            self.process_epoch(i_epoch)

        self.finish_training()

    def _set_output_path(
            self, output_path,
            val_folder_name="validations",
            log_dir_name="log"
    ):
        self.output_path = output_path

        self.output_val_path = os.path.join(self.output_path, val_folder_name)
        if not os.path.exists(self.output_val_path):
            os.makedirs(self.output_val_path)

        self.log_path = os.path.join(self.output_path, log_dir_name)
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

    def save_checkpoint(self, file_name):
        model_file_name = f"{file_name}.pt"
        torch.save(
            self.model,
            os.path.join(self.output_val_path, model_file_name)
        )
        dict_file_name = f"{file_name}.model_state_dict"
        torch.save(
            self.model.state_dict(),
            os.path.join(self.output_val_path, dict_file_name)
        )
        opt_file_name = f"{file_name}.optimizer_state_dict"
        torch.save(
            self.optimizer.state_dict(),
            os.path.join(self.output_val_path, opt_file_name)
        )
