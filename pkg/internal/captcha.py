import asyncio
import os
import uuid
import io
from pathlib import Path
from typing import Union

import aiohttp
import cv2
import numpy as np
from yarl import URL
from dataclasses import dataclass


@dataclass
class DatasetConfig:
    shape = (60, 202, 1)
    labels = "1234567890"
    length: int = 4
    n_sample: int = 1000


class CaptchaSolver:
    def __init__(self, dataset_config: DatasetConfig = DatasetConfig()) -> None:
        self.dataset_config = dataset_config
        self.model = self.__create_model()

    def train_model(self, training_dir: str):
        """ 
        After labeling files in download directory, use this function to build training model
        """
        X, y = self.__preprocess(training_dir)
        return self.model.fit(X, [y[0], y[1], y[2], y[3]], batch_size=32, epochs=60, validation_split=0.2, verbose="0")

    def predict(self, reader: io.BufferedReader) -> str:
        bytes_as_np_array = np.frombuffer(reader.read(), dtype=np.uint8)
        img = cv2.imdecode(bytes_as_np_array, cv2.IMREAD_GRAYSCALE)
        img = img / 255.0

        res = np.array(self.model.predict(img[np.newaxis, :, :, np.newaxis]))

        result = np.reshape(res, (self.dataset_config.length, len(self.dataset_config.labels)))
        k_ind = []
        for i in result:
            k_ind.append(np.argmax(i))

        capt = ''
        for k in k_ind:
            capt += self.dataset_config.labels[k]
        return capt

    def save(self, filepath: str):
        self.model.save_weights(filepath)

    def load(self, filepath: str):
        self.model.load_weights(filepath)

    async def __fetch(self, session, directory: Path, url: URL):
        async with session.get(url) as response:
            with open(directory / (uuid.uuid4().hex + '.jpeg'), 'wb') as fd:
                async for chunk in response.content.iter_chunked(2048):
                    fd.write(chunk)

    async def download_captcha(self, directory: Union[Path, str], url: URL, count: int = 10):
        if isinstance(directory, str):
            directory = Path(directory)
        async with aiohttp.ClientSession() as session:
            functions = [self.__fetch(session, directory, url)
                         for _ in range(count)]
            tasks = asyncio.gather(*functions)
            await tasks

    def __create_model(self):
        from keras.layers import Input, Conv2D, Dense, MaxPooling2D, BatchNormalization, Dropout, Flatten
        from keras.models import Model

        img = Input(shape=self.dataset_config.shape)
        conv1 = Conv2D(16, (3, 3), padding='same', activation='relu')(img)  # 50*200
        mp1 = MaxPooling2D(padding='same')(conv1)  # 25*100
        conv2 = Conv2D(32, (3, 3), padding='same', activation='relu')(mp1)
        mp2 = MaxPooling2D(padding='same')(conv2)  # 13*50
        conv3 = Conv2D(32, (3, 3), padding='same', activation='relu')(mp2)
        bn = BatchNormalization()(conv3)  # to improve the stability of model
        mp3 = MaxPooling2D(padding='same')(bn)  # 7*25

        flat = Flatten()(mp3)  # convert the layer into 1-D

        outs = []
        for _ in range(self.dataset_config.length):
            dens1 = Dense(64, activation='relu')(flat)
            drop = Dropout(0.5)(dens1)  # drops 0.5 fraction of nodes
            res = Dense(len(self.dataset_config.labels), activation='sigmoid')(drop)

            outs.append(res)

        model = Model(img, outs)
        model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=["accuracy"])
        return model

    def __preprocess(self, training_dir: str):
        n_sample = len(os.listdir(training_dir))
        X = np.zeros((n_sample, *self.dataset_config.shape))
        y = np.zeros((self.dataset_config.length, n_sample, len(self.dataset_config.labels)))

        for i, filename in enumerate(os.listdir(training_dir)):
            img = cv2.imread(
                os.path.join(training_dir, filename),
                cv2.IMREAD_GRAYSCALE
            ) / 255  # type: ignore

            label = filename.split('.')[0]
            # There might be more than one sample with the same number
            if label.endswith('_'):
                label = label.replace('_', '')

            img = np.reshape(img, self.dataset_config.shape)  # reshapes image to width 200 , height 50 ,channel 1
            target = np.zeros((self.dataset_config.length, len(self.dataset_config.labels))
                              )  # creates an array of size 5*36 with all entries 0

            for j, k in enumerate(label):
                index = self.dataset_config.labels.find(k)
                target[j, index] = 1

            X[i] = img
            y[:, i] = target

        return X, y
