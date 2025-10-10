from abc import ABC, abstractmethod


class IDatabaseManager(ABC):
    @abstractmethod
    def setup_database(self):
        pass

    @abstractmethod
    def delete_cycle(self):
        pass

    @abstractmethod
    def list_cycles(self):
        pass

    @abstractmethod
    def list_cycle_names(self):
        pass

    @abstractmethod
    def read_cycle_data(self):
        pass
