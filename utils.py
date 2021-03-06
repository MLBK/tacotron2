import torch
import torch.nn.functional as F
from tensorboardX import SummaryWriter
from torch.autograd import Variable
from torch.utils.data import DataLoader
from tqdm import tqdm

from datasets import collate_fn
from text import sequence_to_text
from visualize import show_attention, show_spectrogram


def train(model, optimizer, dataset, num_epochs, batch_size=1, log_interval=50):
    model.train()
    writer = SummaryWriter()
    loader = DataLoader(dataset, batch_size=batch_size, collate_fn=collate_fn)
    step = 0
    for epoch in tqdm(range(num_epochs), total=num_epochs, unit=' epochs'):
        total_loss = 0
        pbar = tqdm(loader, total=len(loader), unit=' batches')
        for b, (text_batch, audio_batch, text_lengths, audio_lengths) in enumerate(pbar):
            text = Variable(text_batch).cuda()
            targets = Variable(audio_batch, requires_grad=False).cuda()

            #  create stop targets
            stop_targets = torch.zeros(targets.size(1), targets.size(0))
            for i in range(len(stop_targets)):
                stop_targets[i, audio_lengths[i] - 1] = 1
            stop_targets = Variable(stop_targets, requires_grad=False).cuda()
 
            outputs, stop_tokens, attention = model(text, targets)
            spec_loss = F.mse_loss(outputs, targets)
            stop_loss = F.binary_cross_entropy_with_logits(stop_tokens, stop_targets)
            loss = spec_loss + stop_loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.data[0]
            pbar.set_description(f'loss: {loss.data[0]:.4f}')
            writer.add_scalar('loss', loss.data[0], step)
            if step % log_interval == 0:
                torch.save(model.state_dict(), f'checkpoints/melnet_{step}.pt')

                # plot the first sample in the batch
                attention_plot = show_attention(attention[0], return_array=True)
                output_plot = show_spectrogram(outputs.data.permute(1, 2, 0)[0],
                                               sequence_to_text(text.data[0]),
                                               return_array=True)
                target_plot = show_spectrogram(targets.data.permute(1, 2, 0)[0],
                                               sequence_to_text(text.data[0]),
                                               return_array=True)

                writer.add_image('attention', attention_plot, step)
                writer.add_image('target', output_plot, step)
                writer.add_image('output', target_plot, step)
            step += 1
