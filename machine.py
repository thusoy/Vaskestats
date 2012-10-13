# coding: utf-8

class Machine(object):
    machine_id = None
    num_machines = 0
    
    def __init__(self, machine_id):
        self.machine_id = machine_id
        Machine.num_machines += 1
        
    def __str__(self):
        return 'Machine #%2d' % self.machine_id
    
    def __repr__(self):
        return self.__str__()

    def __hash__(self):
	return self.machine_id.__hash__()

    def __eq__(self, other):
	return self.machine_id == other.machine_id
    
    def __hash__(self):
        return self.machine_id.__hash__()
    
    def __eq__(self, other):
        return self.machine_id == other.machine_id
    
class BrokenDownMachine(Machine):
    num_broken_down = 0
    
    def __init__(self, machine_id):
        super(BrokenDownMachine, self).__init__(machine_id)
        BrokenDownMachine.num_broken_down += 1

class AvailableMachine(Machine):
    num_available = 0
    
    def __init__(self, machine_id):
        super(AvailableMachine, self).__init__(machine_id)
        AvailableMachine.num_available += 1

class OccupiedMachine(Machine):
    pass

class ClosedMachine(Machine):
    pass

class UnknownMachine(Machine):
    status = None
    num_unknown = 0
    
    def __init__(self, machine_id, status):
        super(UnknownMachine, self).__init__(machine_id)
        self.status = status
        UnknownMachine.num_unknown += 1
        
def get_machine_id(machine_name):
    machine_id = int(machine_name.split()[1])
    return machine_id
