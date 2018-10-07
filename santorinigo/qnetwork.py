import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import optim
from torch.autograd.variable import Variable

class QNetwork(nn.Module):
    def __init__(self, state_size, action_size, nb_hidden, seed=1412):
        super(QNetwork, self).__init__()
        self.seed = torch.manual_seed(seed)
        self.conv_layers = nn.Sequential(
            nn.Conv2d
        )
        self.model = nn.Sequential(
            nn.Linear(state_size, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5)
            nn.Linear(nb_hidden, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5),
            nn.Linear(nb_hidden, action_size)
        )
    def forward(self, state):
        x = self.model(state)
        return(x)

class DuelingNetwork(nn.Module):
    def __init__(self, state_size, action_size, nb_hidden, seed=1412):
        super(DuelingNetwork, self).__init__()
        self.seed = torch.manual_seed(seed)
        
        self.feature = nn.Sequential(
            nn.Linear(state_size, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5)
        )
        
        self.advantage = nn.Sequential(
            nn.Linear(nb_hidden, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5),
            nn.Linear(nb_hidden, action_size)
        )
        
        self.value = nn.Sequential(
            nn.Linear(nb_hidden, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5),
            nn.Linear(nb_hidden, 1)
        )

    def forward(self, state):
        x = self.feature(state)
        adv = self.advantage(x)
        val = self.value(x)
        result = adv + val - adv.mean() 
        return(result)


class NoisyLinear(nn.Module):
    def __init__(self, in_features, out_features, std_init=0.1):
        super(NoisyLinear, self).__init__()
        
        self.in_features  = in_features
        self.out_features = out_features
        self.std_init     = std_init
        
        self.W_mu    = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.W_sigma = nn.Parameter(torch.FloatTensor(out_features, in_features))
        self.register_buffer('W_epsilon', torch.FloatTensor(out_features, in_features))
        
        self.b_mu    = nn.Parameter(torch.FloatTensor(out_features))
        self.b_sigma = nn.Parameter(torch.FloatTensor(out_features))
        self.register_buffer('b_epsilon', torch.FloatTensor(out_features))
        
        self.init_parameters()
        self.reset_noise()
    
    def forward(self, x):
        if self.training: 
            W = self.W_mu + self.W_sigma * Variable(self.W_epsilon)
            b = self.b_mu  + self.b_sigma  * Variable(self.b_epsilon)
        else:
            W = self.W_mu
            b = self.b_mu
        result = F.linear(x, W, b)
        return(result)
    
    def init_parameters(self):
        mu_range = 1 / self.in_features**(1/2)
        
        self.W_mu.data.uniform_(-mu_range, mu_range)
        self.W_sigma.data.fill_(self.std_init / (self.in_features)**(1/2))
        
        self.b_mu.data.uniform_(-mu_range, mu_range)
        self.b_sigma.data.fill_(self.std_init / (self.in_features)**(1/2))
    
    def reset_noise(self):
        epsilon_in  = self.f_noise(self.in_features)
        epsilon_out = self.f_noise(self.out_features)
        
        self.W_epsilon.copy_(epsilon_out.ger(epsilon_in))
        self.b_epsilon.copy_(epsilon_out)
    
    def f_noise(self, size):
        x = torch.randn(size)
        x = x.sign() * (x.abs().sqrt())
        return(x)
    
class NoisyDuelingNetwork(nn.Module):
    def __init__(self, state_size, action_size, nb_hidden, seed=1412):
        super(NoisyDuelingNetwork, self).__init__()
        self.seed = torch.manual_seed(seed)
        self.feature = nn.Sequential(
            nn.Linear(state_size, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5)
        )
        
        self.advantage = nn.Sequential(
            NoisyLinear(nb_hidden, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5),
            NoisyLinear(nb_hidden, action_size)
        )
        
        self.value = nn.Sequential(
            NoisyLinear(nb_hidden, nb_hidden),
            nn.ReLU(),
#             nn.BatchNorm1d(nb_hidden),
#             nn.Dropout(0.5),
            NoisyLinear(nb_hidden, 1)
        )

    def forward(self, state):
        x = self.feature(state)
        adv = self.advantage(x)
        val = self.value(x)
        result = adv + val - adv.mean() 
        return(result)
    
    def reset_noise(self):
#         self._modules['feature'][0].reset_noise()
        self._modules['advantage'][0].reset_noise()
        self._modules['advantage'][2].reset_noise()
        self._modules['value'][0].reset_noise()
        self._modules['value'][2].reset_noise()