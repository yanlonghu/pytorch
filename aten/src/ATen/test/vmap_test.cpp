#include <gtest/gtest.h>

#include <ATen/ATen.h>
#include <ATen/NativeFunctions.h>
#include <ATen/core/op_registration/op_registration.h>
#include <torch/csrc/jit/runtime/operator.h>
#include <torch/torch.h>
#include <ATen/BatchedTensorImpl.h>

using namespace at;

namespace {

TEST(VmapTest, TestBatchedTensor) {
  {
    Tensor x = addBatchDim(ones({2, 3, 4}), /*lvl=*/1, /*dim=*/1);
    std::vector<int64_t> expected_size = {2, 4};
    ASSERT_EQ(x.sizes(), expected_size);
    ASSERT_EQ(x.dim(), 2);
    ASSERT_EQ(x.numel(), 8);
    ASSERT_THROW(x.strides(), c10::Error);
    ASSERT_THROW(x.is_contiguous(), c10::Error);
    ASSERT_THROW(x.storage(), c10::Error);
    ASSERT_THROW(x.storage_offset(), c10::Error);
  }
  {
    // Test multiple batch dims
    Tensor x = addBatchDim(ones({2, 3, 4}), /*lvl=*/1, /*dim=*/1);
    x = addBatchDim(x, /*lvl=*/2, /*dim=*/1);
    std::vector<int64_t> expected_size = {2};
    ASSERT_EQ(x.sizes(), expected_size);
    ASSERT_EQ(x.dim(), 1);
    ASSERT_EQ(x.numel(), 2);
  }
}

}