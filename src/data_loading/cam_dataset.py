import os
import random

import matplotlib.pyplot as plt
import numpy
import torch
from torch.utils.data import Dataset

import cv2


NUM_LANDMARKS = 17


class CameraSequenceDataset(Dataset):
    """
    Данный датасет ориентируется исключительно на имена файлов в папках вида "класс/последовательность".

    Имена файлов служат для построения последовательностей ключей. Они могут быть заменены на простые списки,
    но я решил передать их для наглядности.

    Данные о скелетах загружаются уже из словаря вида "имя файла – скелет", затем скелет нормализуется
    и с шансом 50% горизонтально отражается.

    Поскольку последовательности в папках содержат гораздо больше файлов, чем требуемый seq_len,
    то из папки выбирается случайный срез в методе extract_sequence.

    Данный датасет не учитывает несбалансированность количества последовательностей, но я не успел это переписать.
    """

    SCALING_FACTOR = .8

    def __init__(
            self,
            class_paths: list[str],
            frame_data: dict,
            seq_len: int = 5, seq_step: int = 1,
            device="cpu"
    ):
        self._class_paths = class_paths
        self._seq_len = seq_len
        self._seq_step = seq_step

        self._random = random.Random()

        self._frame_data = frame_data
        self._key_set = set(self._frame_data.keys())

        self._data = None
        self.labels = {}

        self._device = device

        self.fill_data(self._class_paths)

    def extract_entry(self, entry_path):
        entry_files = os.listdir(entry_path)

        files = [f for f in entry_files if f.endswith(".png")]

        if len(files) < len(set(files) & self._key_set):
            print("Not all files are registered at", entry_path)

        entry = [self._frame_data[k][0] for k in sorted(files)]

        return list(entry)

    def extract_sequence(self, entry: list) -> torch.FloatTensor:
        seq_len, seq_step = self._seq_len, self._seq_step

        target_len = seq_len + (seq_step - 1) * (seq_len - 1)
        entry_len = len(entry)
        start_index = 0

        if entry_len < target_len:
            entry = self.stretch_list(entry, target_len)
        elif entry_len > target_len:
            max_first_index = entry_len - target_len
            start_index = self._random.randint(0, max_first_index)

        sequence = entry[start_index:start_index + target_len:seq_step]
        assert len(sequence) == seq_len

        sequence = torch.tensor(sequence, dtype=torch.float)

        sequence = list(map(CameraSequenceDataset.normalize_pose, sequence))

        flip = bool(self._random.getrandbits(1))
        if flip:
            sequence = list(map(CameraSequenceDataset.flip_pose, sequence))

        return torch.stack(sequence)

    def fill_data(self, class_dir_paths):
        data = []

        for label_id, class_dir_path in enumerate(class_dir_paths):
            self.labels[label_id] = os.path.split(class_dir_path)[-1]

            for entry_dir in os.listdir(class_dir_path):
                entry_path = os.path.join(class_dir_path, entry_dir)

                entry = self.extract_entry(entry_path)
                if not entry:
                    continue

                data.append((label_id, entry))

        self._data = data

    @staticmethod
    def stretch_list(input_list, target_length):
        if target_length <= len(input_list):
            return input_list

        repetitions = (target_length // len(input_list)) + 1
        stretched_list = [x for x in input_list for _ in range(repetitions)]
        full_length = len(stretched_list)

        for i in range(full_length - target_length):
            single_side_iteration = i // 2

            if i % 2 == 0:
                index_to_pop = full_length - repetitions - single_side_iteration * repetitions
            else:
                index_to_pop = single_side_iteration * repetitions
            stretched_list.pop(index_to_pop)

        assert len(stretched_list) == target_length

        return stretched_list

    def __getitem__(self, idx: int) -> tuple[torch.FloatTensor, torch.IntTensor]:
        label_id, entry = self._data[idx]

        sequence = self.extract_sequence(entry)
        label_id = torch.tensor(label_id, device=self._device)

        return sequence, label_id

    def __len__(self):
        return len(self._data)

    @staticmethod
    def flip_pose(pose: torch.FloatTensor) -> torch.FloatTensor:
        num_keypoints = pose.size(0)

        ones = torch.ones(num_keypoints)
        zeros = torch.zeros(num_keypoints)

        add = torch.stack((ones, zeros), dim=1)
        mul = torch.stack((-ones, ones), dim=1)

        return pose * mul + add

    @classmethod
    def normalize_pose(cls, pose: torch.FloatTensor) -> torch.FloatTensor:
        x, y = pose.permute((1, 0))
        x_min, x_max = x[x.nonzero()].min(), x[x.nonzero()].max()
        y_min, y_max = y[y.nonzero()].min(), y[y.nonzero()].max()

        # Центрирование
        # x = (x - x_min) + .5 - (x_max - x_min) * .5
        # y = (y - y_min) + .5 - (y_max - y_min) * .5

        factor = cls.SCALING_FACTOR / (y_max - y_min)

        x = (x - x_min) * factor + .5 - (x_max - x_min) * .5 * factor
        y = (y - y_min) * factor + .5 - (y_max - y_min) * .5 * factor

        normalized_pose = torch.stack((x, y), dim=1)
        normalized_pose[pose.prod(dim=1) == 0] = torch.zeros([2])

        return normalized_pose
