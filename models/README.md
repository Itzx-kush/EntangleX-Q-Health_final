# Trusted model artifacts

This folder starts without trained models. The application writes UUID-named dill bundles only after actual training and evaluation. These bundles contain executable serialized objects: load only application-created artifacts with their protected registry hashes. Do not upload, copy, or substitute untrusted model files. Generation is not training, and an empty folder is intentional.
