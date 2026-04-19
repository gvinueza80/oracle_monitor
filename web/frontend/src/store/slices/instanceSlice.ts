import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface Instance {
  id: string;
  name: string;
  host: string;
  port: number;
  serviceName: string;
  enabled: boolean;
  connectionStatus: string;
  lastConnectionCheck: string;
  createdAt: string;
}

interface InstanceState {
  instances: Instance[];
  selectedInstanceId: string | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: InstanceState = {
  instances: [],
  selectedInstanceId: localStorage.getItem('selectedInstanceId'),
  isLoading: false,
  error: null,
};

export const instanceSlice = createSlice({
  name: 'instances',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setInstances: (state, action: PayloadAction<Instance[]>) => {
      state.instances = action.payload;
    },
    selectInstance: (state, action: PayloadAction<string>) => {
      state.selectedInstanceId = action.payload;
      localStorage.setItem('selectedInstanceId', action.payload);
    },
    addInstance: (state, action: PayloadAction<Instance>) => {
      state.instances.push(action.payload);
    },
    updateInstance: (state, action: PayloadAction<Instance>) => {
      const index = state.instances.findIndex((i) => i.id === action.payload.id);
      if (index !== -1) {
        state.instances[index] = action.payload;
      }
    },
    deleteInstance: (state, action: PayloadAction<string>) => {
      state.instances = state.instances.filter((i) => i.id !== action.payload);
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setLoading,
  setInstances,
  selectInstance,
  addInstance,
  updateInstance,
  deleteInstance,
  setError,
} = instanceSlice.actions;
export default instanceSlice.reducer;
