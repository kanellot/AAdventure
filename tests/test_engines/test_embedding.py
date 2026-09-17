"""Pruebas unitarias para el motor y backends de embeddings semánticos."""

import unittest
from engines.embedding import EmbeddingEngine, EmbeddingFactory, MockEmbeddingBackend


class TestEmbeddingEngine(unittest.TestCase):
    """Verifica el cálculo de similitudes semánticas y la fábrica de backends."""

    def test_mock_backend_tokenization_and_similarity(self):
        backend = MockEmbeddingBackend()
        tokens = backend.embed_text("El guerrero ataca al dragón en la cueva")
        self.assertIsInstance(tokens, set)
        self.assertIn("guerrero", tokens)
        self.assertIn("dragon", {w.replace("ó", "o") for w in tokens} | tokens)

        # Similitud alta con frases relacionadas
        vec1 = backend.embed_text("caballero armadura escudo")
        vec2 = backend.embed_text("escudo y espada del caballero")
        sim_high = backend.compute_similarity(vec1, vec2)
        self.assertGreater(sim_high, 0.2)

        # Similitud cero con frases completamente inconexas
        vec3 = backend.embed_text("computadora satelite algoritmo")
        sim_zero = backend.compute_similarity(vec1, vec3)
        self.assertEqual(sim_zero, 0.0)

    def test_mock_backend_max_similarity(self):
        backend = MockEmbeddingBackend()
        query = "quiero una cerveza en la taberna"
        targets = [
            "servir bebida en la taberna",
            "el clima esta frio hoy",
            "atacar con arco y flecha",
        ]
        score, best_match = backend.compute_max_similarity(query, targets)
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0.0)
        self.assertEqual(best_match, "servir bebida en la taberna")

    def test_embedding_factory_mock(self):
        backend = EmbeddingFactory.get_backend(backend_type="mock", force_new=True)
        self.assertIsInstance(backend, MockEmbeddingBackend)

    def test_embedding_engine_facade(self):
        backend = MockEmbeddingBackend()
        engine = EmbeddingEngine(backend=backend)
        vec = engine.embed_text("hola mundo")
        self.assertIsInstance(vec, set)

        score, best = engine.compute_max_similarity("hola", ["hola mundo", "adios"])
        self.assertEqual(best, "hola mundo")
        self.assertGreater(score, 0.0)


if __name__ == "__main__":
    unittest.main()
