from torch import nn


class PlainSequence(nn.Module):
    def __init__(self, seq_len, lm_num, label_num):
        super(PlainSequence, self).__init__()

        self.name = "plain_sequence_network"

        dim = 2
        input_size = seq_len * lm_num * dim

        print(input_size)

        hidden_size = 1024
        output_size = label_num

        self.input_layer = nn.Sequential(
            nn.Linear(input_size, hidden_size // 4),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
        )

        self.layer_2n = nn.Sequential(
            nn.Linear(hidden_size // 4, hidden_size // 2),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
        )
        self.layer_1n = nn.Sequential(
            nn.Linear( hidden_size // 2, hidden_size),
            nn.Dropout(p=.1),
            nn.ReLU(inplace=True)
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
        x = self.layer_2n(x)
        x = self.layer_1n(x)
        x = self.layer_0(x)
        x = self.layer_1(x)
        x = self.layer_2(x)
        x = self.output_layer(x)

        return x
