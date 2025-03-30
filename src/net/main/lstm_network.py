import sys

import torch
from torch import nn


class LSTM_Network(nn.Module):
    def __init__(self, seq_len, lm_num, label_num):
        super(LSTM_Network, self).__init__()

        self.name = "lstm_network"

        dim = 2
        input_size = seq_len * lm_num * dim

        print(input_size)

        hidden_size = 1024
        output_size = label_num

        self.input_layer = nn.Sequential(
            nn.Linear(input_size, input_size),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
        )

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            batch_first=True
        )

        self.layer_0 = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
        )
        self.layer_1 = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
        )
        self.layer_2 = nn.Sequential(
            nn.Linear(hidden_size // 2, hidden_size // 4),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
        )

        self.output_layer = nn.Sequential(
            nn.Linear(hidden_size // 4, output_size),
            nn.Softmax(dim=1)
        )

    def forward(self, x):
        batch_size = x.size(0)

        x = x.view(batch_size, -1)

        x = self.input_layer(x)

        x, (x_0, x_1) = self.lstm(x)

        x = self.layer_0(x)
        x = self.layer_1(x)
        x = self.layer_2(x)

        x = self.output_layer(x)

        return x


if __name__ == "__main__":
    seq_len, lm_num, dim_num = 10, 17, 2
    class_num = 20
    model = LSTM_Network(seq_len, lm_num, class_num)
    output = model(torch.rand(16, seq_len, lm_num, dim_num))
    print(output.shape)
