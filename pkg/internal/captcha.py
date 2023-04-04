import asyncio
import os
import pickle
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
from typing import Union

import aiohttp
import cv2
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder
from yarl import URL


class CaptchaML:
    def __init__(self) -> None:
        self.clf = MLPClassifier(random_state=0, max_iter=500)

    def train_model(self, training_dir: Union[Path, str]):
        """ 
        After labeling files in download directory, use this function to build training model
        """

        tmp_dir = tempfile.mkdtemp()

        files = os.listdir(training_dir)
        for file_name in files:
            img = cv2.imread(
                os.path.join(training_dir, file_name),
                cv2.IMREAD_GRAYSCALE
            )
            img = self.__prepare_image(img)

            cv2.imwrite(
                os.path.join(tmp_dir, f'{file_name.split(".")[0]}.jpeg'), img)

        le = LabelEncoder()
        values = list(range(0, 10))
        le.fit(values)

        files = os.listdir(tmp_dir)
        X = []
        y = []
        for file_name in files:
            number = file_name.split('.')[0]
            img = cv2.imread(
                os.path.join(tmp_dir, file_name), cv2.IMREAD_UNCHANGED)

            for i in range(4):
                X.append(
                    img[:, i*(202//4): (i+1)*(202//4)].reshape([3000]).astype('bool'))
                y.append(int(number[i]))

        X = np.array(X)
        y = le.transform(y)

        self.clf.fit(X, y)

    def predict_captcha(self, reader: BytesIO) -> str:
        bytes_as_np_array = np.frombuffer(reader.read(), dtype=np.uint8)
        img = cv2.imdecode(bytes_as_np_array, cv2.IMREAD_GRAYSCALE)
        # For debug only
        cv2.imwrite('./captcha.jpeg', img)
        img = self.__prepare_image(img)

        captcha = ""
        for i in range(4):
            digit = self.clf.predict(
                img[:, i*(202//4): (i+1)*(202//4)].reshape([3000]).astype('bool').reshape(1, -1))
            if digit:
                captcha += str(digit[0])

        print('guest was', captcha)
        return captcha

    def save(self, model_file: str):
        with open(model_file, 'wb') as fd:
            pickle.dump(self.clf, fd)

    def load(self, model_file: str):
        with open(model_file, 'rb') as fd:
            self.clf = pickle.load(fd)

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

    def __prepare_image(self, img):
        """ Convert image to specific format. """

        # Remove noise
        img = cv2.fastNlMeansDenoising(
            img, None, 20, 7, 21)  # type: ignore

        # Convert to binary
        (thresh, img) = cv2.threshold(
            img,
            180,
            255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )

        return img
