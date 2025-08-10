import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Tuple
import metal

class MetalOptimizedLayer(nn.Module):
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(out_features, in_features) * 0.01)
        self.bias = nn.Parameter(torch.zeros(out_features))
        
        self.device = metal.Device()
        self.queue = self.device.makeCommandQueue()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.device.type == 'mps':
            return self._metal_forward(x)
        return F.linear(x, self.weight, self.bias)
        
    def _metal_forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, in_features = x.shape
        out_features = self.weight.shape[0]
        
        x_metal = self.device.makeBuffer(length=x.numel() * 4, options=metal.ResourceStorageModeShared)
        w_metal = self.device.makeBuffer(length=self.weight.numel() * 4, options=metal.ResourceStorageModeShared)
        b_metal = self.device.makeBuffer(length=self.bias.numel() * 4, options=metal.ResourceStorageModeShared)
        out_metal = self.device.makeBuffer(length=batch_size * out_features * 4, options=metal.ResourceStorageModeShared)
        
        x_metal.contents().as_buffer(x.numel() * 4)[:] = x.cpu().numpy().astype(np.float32).tobytes()
        w_metal.contents().as_buffer(self.weight.numel() * 4)[:] = self.weight.cpu().numpy().astype(np.float32).tobytes()
        b_metal.contents().as_buffer(self.bias.numel() * 4)[:] = self.bias.cpu().numpy().astype(np.float32).tobytes()
        
        kernel_source = """
        #include <metal_stdlib>
        using namespace metal;
        
        kernel void matmul_relu(
            device float* x [[buffer(0)]],
            device float* w [[buffer(1)]],
            device float* b [[buffer(2)]],
            device float* out [[buffer(3)]],
            constant uint& batch_size [[buffer(4)]],
            constant uint& in_features [[buffer(5)]],
            constant uint& out_features [[buffer(6)]],
            uint2 gid [[thread_position_in_grid]]
        ) {
            uint batch_idx = gid.x;
            uint out_idx = gid.y;
            
            if (batch_idx >= batch_size || out_idx >= out_features) return;
            
            float sum = b[out_idx];
            for (uint i = 0; i < in_features; i++) {
                sum += x[batch_idx * in_features + i] * w[out_idx * in_features + i];
            }
            out[batch_idx * out_features + out_idx] = max(sum, 0.0f);
        }
        """
        
        library = self.device.makeLibrary(source=kernel_source, options=None)
        function = library.makeFunction(name="matmul_relu")
        pipeline = self.device.makeComputePipelineState(function=function)
        
        command_buffer = self.queue.makeCommandBuffer()
        encoder = command_buffer.makeComputeCommandEncoder()
        encoder.setComputePipelineState(pipeline)
        encoder.setBuffer(x_metal, 0, 0)
        encoder.setBuffer(w_metal, 0, 1)
        encoder.setBuffer(b_metal, 0, 2)
        encoder.setBuffer(out_metal, 0, 3)
        encoder.setBytes(batch_size.to_bytes(4, 'little'), 4)
        encoder.setBytes(in_features.to_bytes(4, 'little'), 5)
        encoder.setBytes(out_features.to_bytes(4, 'little'), 6)
        
        grid_size = metal.Size(batch_size, out_features, 1)
        thread_group_size = metal.Size(min(32, batch_size), min(32, out_features), 1)
        encoder.dispatchThreads(grid_size, thread_group_size)
        encoder.endEncoding()
        
        command_buffer.commit()
        command_buffer.waitUntilCompleted()
        
        result = np.frombuffer(out_metal.contents().as_buffer(batch_size * out_features * 4), dtype=np.float32)
        return torch.from_numpy(result.reshape(batch_size, out_features)).to(x.device)
