import numpy as np
from scipy.sparse import issparse
from chunkdot.chunkdot import chunkdot
from chunkdot.utils import get_chunk_size_per_thread


def cosine_similarity_top_k(
    embeddings: np.ndarray,
    top_k: int,
    normalize: bool = True,
    max_memory: int = None,
    force_memory: bool = False,
):
    """Calculate cosine similarity and only keep the K most similar items for each item.

    Args:
        embeddings (np.array): 2D array containing the items embeddings. Array of size
            number of items x embedding dimension.
        top_k (int): The amount of similar items per item to return.
        normalize (bool): If to apply L2-norm to each row.
            Default True.
        max_memory (int): Maximum amount of memory to use in bytes. If None it will use the
            available memory to the system according to chunkdot.utils.get_memory_available.
            Default None.
        force_memory (bool): Use max_memory even if it is bigger than the memory
            available. This can be desired if the cosine similarity calculation is used many times
            within the same Python process, such that objects are garbage collected but memory is
            not marked as available to the OS. In this case is advised to set max_memory
            to chunkdot.utils.get_memory_available at the start of your Python process.
            Default False.

    Returns:
        scipy.sparse.csr_matrix: Sparse matrix containing non-zero values only for the K most
            similar items per item.

    Raises:
        ValueError:

    This will:
        1. Normalize the rows in the "embeddings" matrix to have unit L2 norm.
        2. Calculate the optimal number of rows per piece when splitting the embeddings matrix.
        3. Parallelize the matrix multiplication using a separate piece in each thread.
        4. Per thread:
            a. Matrix multiplication between the piece and the embeddings matrix transposed.
            b. Extract the values and column indices of the most similar K items per row.
            c. Collect such values and column indices into outer scope arrays.
        5. Create a CSR matrix from all values and indices and return it.
    """
    if issparse(embeddings):
        raise TypeError("ChunkDot does not yet support SciPy sparse matrices as input.")

    # return type consistent with sklearn.pairwise.cosine_similarity function
    return_type = "float32" if embeddings.dtype == np.float32 else "float64"
    if normalize:
        embeddings = (
            embeddings
            / np.sqrt(np.einsum("ij,ij->i", embeddings, embeddings, dtype=return_type))[
                :, np.newaxis
            ]
        )

    n_rows = len(embeddings)
    abs_top_k = abs(top_k)

    if abs_top_k >= n_rows:
        raise ValueError(
            f"The number of requested similar items (top_k={abs_top_k}) must be less than the "
            f"total number of items (len(embeddings)={len(embeddings)})"
        )

    chunk_size_per_thread = get_chunk_size_per_thread(n_rows, abs_top_k, max_memory, force_memory)
    similarities = chunkdot(embeddings, embeddings.T, top_k, chunk_size_per_thread, return_type)
    return similarities
